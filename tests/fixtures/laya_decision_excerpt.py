# 从用户 HTML 的嵌入快照提取，仅用于静态分析回归；不是完整 common.py，不执行。




























































































































































































































































































































































































































































































































































































class DecisionModel(nn.Module):
    """Bidirectional transformer encoder backbone + typed decision head."""

    def __init__(self, encoder: nn.Module, head_layers: int = 2, n_act: int = 2, dropout: float = 0.1,
                 no_init: bool = False):
        super().__init__()
        self.encoder = encoder
        d = encoder.config.hidden_size
        # `no_init` means the caller is about to load every parameter from a checkpoint, so the
        # head's initial values are pure overhead -- and not just time. transformers'
        # `no_init_weights()` patches the torch.nn.init functions, but something inside
        # nn.TransformerEncoderLayer draws from the RNG outside them, so building it still
        # advanced the global generator and made `load()` a visible side effect. On the meta
        # device no initialisation kernel runs at all; the layers are materialised empty and the
        # load fills them.
        with torch.device("meta") if no_init else nullcontext():
            nhead = max(1, d // 64)
            layer = nn.TransformerEncoderLayer(d, nhead, 4 * d, dropout, batch_first=True, norm_first=True)
            # The stock attention bakes the traced length into an exported graph; see
            # _DynamicMultiheadAttention. Same parameters, same maths, traceable shapes.
            layer.self_attn = _DynamicMultiheadAttention(d, nhead, dropout=dropout, batch_first=True)
            self.head = nn.TransformerEncoder(layer, head_layers, enable_nested_tensor=False) if head_layers > 0 else None
            self.type_emb = nn.Embedding(3, d)
            self.scorer = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
            self.act_head = nn.Sequential(nn.Linear(d + 4, 256), nn.GELU(), nn.Linear(256, n_act))
            self.register_buffer("temperature", torch.ones(3))
        if no_init:
            # Only the modules created above are on the meta device; the encoder is already real
            # and may hold non-persistent buffers (RoPE frequencies) that to_empty would wipe.
            for module in (self.head, self.type_emb, self.scorer, self.act_head):
                if module is not None:
                    module.to_empty(device="cpu")
            self.temperature = torch.empty_like(self.temperature, device="cpu")
        self.head_checkpointing = False

    def forward(self, input_ids, attention_mask, marker_pos, marker_mask, qtype, detach_encoder: bool = False,
                position_ids=None, option_ids=None):
        if option_ids is None:
            h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        else:
            # Parallel option layout (`parallel_layout`). The head below has no positional
            # encoding, so with order-blind marker embeddings the logits permute with the options.
            masks = parallel_option_masks(attention_mask, position_ids, option_ids,
                                          getattr(self.encoder.config, "sliding_window", None))
            h = self.encoder(input_ids=input_ids, attention_mask=masks, position_ids=position_ids).last_hidden_state
        if detach_encoder:
            h = h.detach()
        h = h + self.type_emb(qtype)[:, None, :]
        if self.head is not None:
            pad = ~attention_mask.bool()
            for layer in self.head.layers:
                if self.head_checkpointing and self.training and torch.is_grad_enabled():
                    # Non-reentrant checkpointing also trains the head when its input
                    # is frozen. Default RNG preservation keeps dropout consistent.
                    h = checkpoint(layer, h, src_key_padding_mask=pad, use_reentrant=False)
                else:
                    h = layer(h, src_key_padding_mask=pad)
        idx = marker_pos.clamp(min=0)[:, :, None].expand(-1, -1, h.size(-1))
        m = torch.gather(h, 1, idx)
        logits = self.scorer(m).squeeze(-1).float()
        logits = logits.masked_fill(~marker_mask, -1e4)

        p = torch.softmax(logits.detach(), -1)
        k = marker_mask.sum(-1).clamp(min=2).float()
        ent = -(p * torch.log(p.clamp_min(1e-9))).sum(-1) / torch.log(k)
        if p.size(-1) >= 2:
            top2 = p.topk(2, -1).values
        else:
            # A single-option question has exactly one marker, so p.topk(2, ...)
            # has nothing to select for the second slot and raises. The answer
            # is still well-defined: softmax over one logit is 1.0 regardless of
            # its value, so pad the missing second entry with 0.0 - that gives
            # the act head top1 - top2 == 1.0, the same "fully decided" signal
            # it would see for any other unambiguous top-1-vs-rest gap.
            top1 = p.topk(1, -1).values
            top2 = torch.cat([top1, torch.zeros_like(top1)], dim=-1)
        feats = torch.stack([top2[:, 0], top2[:, 0] - top2[:, 1], ent, k / 255.0], -1)
        pooled = h[:, 0].float()
        act_input = torch.cat([pooled, feats], -1)
        # Explicit-dtype exports run without autocast; keep the confidence maths in fp32,
        # then match the head's weights. Autocast already chooses the linear's input dtype.
        if not _autocast_enabled(h.device.type):
            act_input = act_input.to(self.act_head[0].weight.dtype)
        act_logits = self.act_head(act_input)
        return logits, act_logits

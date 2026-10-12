"""教学 Decoder：无 RoPE、无 KV cache、无 dropout，不兼容官方权重。"""
import math
import torch
from torch import nn
from torch.nn import functional as F


class RMSNorm(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(c['hidden_size']))

    def forward(self, x):
        variance = x.pow(2).mean(-1, keepdim=True)
        normalized = x * torch.rsqrt(variance + 1e-6)
        return normalized * self.weight


class Attention(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.h = c['num_attention_heads']
        self.kv = c['num_key_value_heads']
        self.d = c['head_dim']
        hidden = c['hidden_size']
        bias = c['projection_bias']
        self.q_proj = nn.Linear(hidden, self.h * self.d, bias=bias)
        self.k_proj = nn.Linear(hidden, self.kv * self.d, bias=bias)
        self.v_proj = nn.Linear(hidden, self.kv * self.d, bias=bias)
        self.o_proj = nn.Linear(hidden, hidden, bias=bias)

    def forward(self, x):
        b, t, _ = x.shape
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)
        q = q.reshape(b, t, self.h, self.d).transpose(1, 2)
        k = k.reshape(b, t, self.kv, self.d).transpose(1, 2)
        v = v.reshape(b, t, self.kv, self.d).transpose(1, 2)
        k = k.repeat_interleave(self.h // self.kv, dim=1)
        v = v.repeat_interleave(self.h // self.kv, dim=1)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d)
        mask = torch.ones(t, t, device=x.device, dtype=torch.bool).tril()
        scores = scores.masked_fill(~mask, float('-inf'))
        weights = torch.softmax(scores, dim=-1)
        context = torch.matmul(weights, v)
        context = context.transpose(1, 2).contiguous().reshape(b, t, self.h * self.d)
        return self.o_proj(context)


class GatedMLP(nn.Module):
    def __init__(self, c):
        super().__init__()
        hidden, intermediate = c['hidden_size'], c['intermediate_size']
        self.gate_proj = nn.Linear(hidden, intermediate, bias=False)
        self.up_proj = nn.Linear(hidden, intermediate, bias=False)
        self.down_proj = nn.Linear(intermediate, hidden, bias=False)

    def forward(self, x):
        gate = self.gate_proj(x)
        up = self.up_proj(x)
        activated = F.silu(gate)
        product = activated * up
        return self.down_proj(product)


class DecoderBlock(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.norm1 = RMSNorm(c)
        self.attention = Attention(c)
        self.norm2 = RMSNorm(c)
        self.mlp = GatedMLP(c)

    def forward(self, x):
        normalized = self.norm1(x)
        attended = self.attention(normalized)
        x = x + attended
        normalized = self.norm2(x)
        transformed = self.mlp(normalized)
        return x + transformed


class MiniDecoder(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.embedding = nn.Embedding(c['vocab_size'], c['hidden_size'])
        self.blocks = nn.ModuleList([DecoderBlock(c) for _ in range(c['num_layers'])])
        self.final_norm = RMSNorm(c)
        self.lm_head = nn.Linear(c['hidden_size'], c['vocab_size'], bias=False)

    def forward(self, tokens):
        x = self.embedding(tokens)
        for block in self.blocks:
            x = block(x)
        x = self.final_norm(x)
        return self.lm_head(x)

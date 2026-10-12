"""供静态分析边界测试的小模型，未使用未知源码运行采样。"""
import torch
from torch import nn

class SequentialResidual(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.projection = nn.Linear(4, 4, bias=False)
        self.activation = nn.ReLU()
    def forward(self, x):
        y = self.projection(x)
        y = self.activation(y)
        return x + y

class BranchShared(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.left = nn.Linear(4, 4, bias=False)
        self.right = self.left
        self.unused = nn.Linear(4, 2, bias=False)
    def forward(self, x):
        a = self.left(x)
        b = self.left(x)
        c = self.right(x)
        joined = torch.cat([a, b, c], dim=-1)
        return joined, a

class DynamicBranch(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.proj = nn.Linear(4, 4)
    def forward(self, x):
        if x.sum() > 0:
            return self.proj(x)
        return x

class HeterogeneousRepeat(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(4, 4), nn.Linear(4, 8)])
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

# GNN that attempts to match clusters to groups
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import torch
import numpy as np
from torch.nn import Sequential as Seq, Linear as Lin, ReLU, Sigmoid, LeakyReLU, Dropout, BatchNorm1d
from torch_geometric.nn import MetaLayer, GATConv

class EdgeNodeOnlyModel(torch.nn.Module):
    """
    Model that runs edge weights + node weights through a MLP for predictions
    
    """
    def __init__(self, cfg):
        super(EdgeNodeOnlyModel, self).__init__()
        
        if 'modules' in cfg:
                self.model_config = cfg['modules']['edge_only']
        else:
            self.model_config = cfg

        self.leak = self.model_config.get('leak', 0.1)

        self.bn_node = BatchNorm1d(16)
        self.bn_edge = BatchNorm1d(10)
        
        self.edge_pred_mlp = Seq(
            Lin(42, 64),
            LeakyReLU(self.leak),
            Lin(64, 64),
            LeakyReLU(self.leak),
            Lin(64,32),
            LeakyReLU(self.leak),
            Lin(32,16),
            LeakyReLU(self.leak),
            Lin(16,2)
        )
        
        def edge_pred_model(source, target, edge_attr, u, batch):
            out = torch.cat([source, target, edge_attr], dim=1)
            out = self.edge_pred_mlp(out)
            return out
        
        self.edge_predictor = MetaLayer(edge_pred_model, None, None)
    
    def forward(self, x, edge_index, e, xbatch):
        
        e = self.bn_edge(e)
        x = self.bn_node(x)
        
        x, e, u = self.edge_predictor(x, edge_index, e, u=None, batch=xbatch)
        
        return {
            'edge_pred': e
        }
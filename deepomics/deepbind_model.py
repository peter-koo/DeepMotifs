import sys
import collections

sys.path.append('..')
from deepomics.build_network import build_network 

def model(input_shape, output_shape):

	layer1 = {'layer': 'input',
			  'shape': input_shape
			  }
	layer2 = {'layer': 'conv1d', 
			  'num_filters': 20,  #240
			  'filter_size': 24,
			  'activation': 'relu',
			  'global_pool': 'max',
			  }
	layer3 = {'layer': 'dense', 
			  'num_units': 100,
			  'norm': 'batch',
			  'activation': 'relu',
			  'dropout': 0.5,
			  }
	layer4 = {'layer': 'dense', 
			  'num_units': output_shape[1],
			  'activation': 'sigmoid',
			  }
		  
	model_layers = [layer1, layer2, layer3, layer4]
	network, placeholders = build_network(model_layers, output_shape, supervised=True)

	# optimization parameters
	optimization = {"objective": "binary",
					"optimizer": "adam",
					"learning_rate": 0.001,      
					"l2": 1e-6,
					# "l1": 0, 
					}


	return network, placeholders, optimization


#/bin/python
"""
Data sets:
	'load_DeepSea',
	'load_MotifSimulation_categorical'
	'load_MotifSimulation_categorical'
"""

def load_data(model_name, filepath, options=[]):

	# load and build model parameters
	if model_name == "DeepSea":
		from .DeepSea import *
		if "num_include" in options:
			num_include = options["num_include"]
		else:
			num_include = 4400000
		if "class_range" in options:
			class_range = options["class_range"]
		else:
			class_range = range(918)
		train, valid, test = DeepSea(filepath, num_include, class_range)

	elif model_name == "MotifSimulation_binary":
		from .MotifSimulation_binary import *
		train, valid, test = MotifSimulation_binary(filepath)

	elif model_name == "MotifSimulation_categorical":
		from .MotifSimulation_categorical import * 
		train, valid, test = MotifSimulation_categorical(filepath)


	return train, valid, test
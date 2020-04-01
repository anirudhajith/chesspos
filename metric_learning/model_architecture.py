import tensorflow as tf
from tensorflow import keras


class TripletLossLayer(keras.layers.Layer):
	def __init__(self, alpha, **kwargs):
		self.alpha = alpha
		super(TripletLossLayer, self).__init__(**kwargs)

	def triplet_loss(self, inputs):
		anchor, positive, negative = inputs
		pos_dist = tf.reduce_sum(tf.square(anchor-positive), axis=-1)
		neg_dist = tf.reduce_sum(tf.square(anchor-negative), axis=-1)
		return tf.reduce_sum(tf.maximum(pos_dist - neg_dist + self.alpha, 0), axis=0)

	def call(self, inputs):
		loss = self.triplet_loss(inputs)
		self.add_loss(loss)
		return loss

def embedding_network(input_shape, embedding_size, hidden_layers=None):
	if hidden_layers is None:
		return keras.layers.Dense(
			embedding_size, activation='relu', input_shape=input_shape,name="embedding_layer"
		)
	else:
		embedding = keras.Sequential(name="embedding_model")
		embedding.add(
			keras.layers.Dense(hidden_layers[0], activation='relu',
				input_shape=input_shape,name="embedding_layer_0"
			)
		)
		for i in range(1, len(hidden_layers)-1):
			embedding.add(
				keras.layers.Dense(hidden_layers[i], activation='relu',name=f"embedding_layer_{i}")
			)
		embedding.add(
			keras.layers.Dense(embedding_size, activation='relu',
				name=f"embedding_layer_{len(hidden_layers)}"
			)
		)
		return embedding


def triplet_network_model(input_shape, embedding_size, hidden_layers=None, alpha=0.2):
	# Input layers
	anchor_input = keras.layers.Input(input_shape, name="anchor_input", dtype=float)
	positive_input = keras.layers.Input(input_shape, name="positive_input", dtype=float)
	negative_input = keras.layers.Input(input_shape, name="negative_input", dtype=float)

	# Generate the encodings (feature vectors) for the three positions
	embedding = embedding_network(input_shape, embedding_size, hidden_layers=hidden_layers)
	embedding.summary()

	# Embeddings for the three inputs
	embedding_a = embedding(anchor_input)
	embedding_p = embedding(positive_input)
	embedding_n = embedding(negative_input)

	# TripletLoss Layer, initialize and incorporate into network, tie embeddings together
	loss_layer = TripletLossLayer(alpha=alpha, name='triplet_loss_layer')([embedding_a, embedding_p, embedding_n])

	# Cast as tf model
	triplet_network = keras.models.Model(
		inputs=[anchor_input, positive_input, negative_input],
		outputs=[loss_layer, embedding_a, embedding_p, embedding_n]
	)

	# Compile the model
	optimizer = keras.optimizers.Adam(lr=0.00006)

	def mean_pred(y_true, y_pred): # pylint: disable=unused-argument,dangerous-default-value
		return print("hello")

	triplet_network.compile(
		loss=None,
		optimizer=optimizer,
		metrics=[mean_pred] # call to any metric not working, why?
	)

	# Print model summary
	triplet_network.summary()

	return triplet_network
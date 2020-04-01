import os

import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt

from triplet_preparation import train_inputs_file_array_generator, train_inputs_length
from model_architecture import triplet_network_model

print(f"tf.__version__: {tf.__version__}") # pylint: disable=no-member
print(f"tf.keras.__version__: {tf.keras.__version__}")

'''
Inputs
'''
# environment
model_dir = os.path.abspath('metric_learning/model/simple_triplet')
train_dir = os.path.abspath('data/train_small')
validation_dir = os.path.abspath('data/validation_small')
save_metrics = True
hide_warnings = True
plot_model = True
# model specs
input_shape = (773,)
embedding_size = 10
# training specs
train_batch_size = 16
validation_batch_size = 16
train_steps_per_epoch = 1000
validation_steps_per_epoch = 10
yield_augmented = 1

'''
Training environment
'''
if hide_warnings:
	os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' # hide warnings during training

'''
Define custom callback to monitor a custom metric on epoch end
'''
class SkMetrics(keras.callbacks.Callback):
	def __init__(self, valid_data, batch_size, steps_per_callback=10):
		super(SkMetrics, self).__init__()
		self.valid_data = valid_data
		self.batch_size = batch_size
		self.steps_per_callback = steps_per_callback

	def predict_correct(self, predictions):
		anchor = predictions[1]
		positive = predictions[2]
		negative = predictions[3]
		pos_dist = tf.reduce_sum(tf.square(anchor-positive), axis=-1)
		neg_dist = tf.reduce_sum(tf.square(anchor-negative), axis=-1)
		return tf.reduce_sum(tf.cast(pos_dist < neg_dist, dtype=tf.int32), axis=0)

	def on_train_begin(self, logs={}): # pylint: disable=unused-argument,dangerous-default-value
		self.num_correct = [] # pylint: disable=attribute-defined-outside-init
		self.frac_correct = [] # pylint: disable=attribute-defined-outside-init
		self.diagnostics = [] # pylint: disable=attribute-defined-outside-init

	def on_epoch_end(self, epoch, logs={}): # pylint: disable=unused-argument,dangerous-default-value
		correct = tf.Variable(0)
		self.diagnostics.append("correct variable initialized")
		for i in range(self.steps_per_callback):
			predictions = self.model.predict_on_batch(next(self.valid_data))
			self.diagnostics.append(f"prediction {i} successful")
			correct.assign_add(self.predict_correct(predictions))
			self.diagnostics.append("correct variable updated")
		self.num_correct.append(correct)
		frac = tf.cast(correct, dtype=tf.float16)/tf.Variable(self.batch_size*self.steps_per_callback, dtype=tf.float16)
		self.frac_correct.append(frac.numpy())
		print(f" triplet_acc: {self.frac_correct[-1]}")


'''
Initialize triplet network
'''
model = triplet_network_model(input_shape, embedding_size, hidden_layers=[512,256,64])
if plot_model:
	keras.utils.plot_model(model, model_dir+'/triplet_network.png', show_shapes=True)

'''
Initialise trainig, and validation data
'''
train_files = [
	os.path.abspath('data/train_small/lichess_db_standard_rated_2013-02-tuples.h5'),
	os.path.abspath('data/train_large/lichess_db_standard_rated_2013-03-tuples.h5'),
	os.path.abspath('data/train_large/lichess_db_standard_rated_2013-04-tuples.h5')
]
validation_files = [
	os.path.abspath('data/validation_small/lichess_db_standard_rated_2013-01-tuples.h5')
]

# TODO: print WARNING if too few validation examples
train_len = train_inputs_length(train_files, table_id_prefix="tuples")
val_len = train_inputs_length(validation_files, table_id_prefix="tuples")
print(f"\n{train_len} training samples.")
print(f"{val_len} validation samples.")

# generators for train and test data
train_generator = train_inputs_file_array_generator(train_files, table_id_prefix="tuples",
					tuple_indices=[0,1,2,3,4,5,6], batch_size=train_batch_size)
validation_generator = train_inputs_file_array_generator(validation_files, table_id_prefix="tuples",
					tuple_indices=[0,1,2,3,4,5,6], batch_size=validation_batch_size)
metric_generator = train_inputs_file_array_generator(validation_files, table_id_prefix="tuples",
					tuple_indices=[0,1,2,3,4,5,6], batch_size=validation_batch_size)

# instantiate callbacks
skmetrics = SkMetrics(metric_generator, batch_size=validation_batch_size, steps_per_callback=10)
early_stopping = keras.callbacks.EarlyStopping(
	monitor='val_loss', min_delta=0.1, patience=10, verbose=0, mode='min'
)

'''Train  the model'''
history = model.fit(
	train_generator,
	steps_per_epoch=train_steps_per_epoch,
	epochs=int(yield_augmented*train_len/train_steps_per_epoch/train_batch_size),
	validation_data=validation_generator,
	validation_steps=validation_steps_per_epoch,
	callbacks=[skmetrics, early_stopping]
)

print('history dict:', history.history.keys())

loss = history.history['loss']
val_loss = history.history['val_loss']
triplet_accuracy = skmetrics.frac_correct

plt.figure()
plt.plot(np.arange(len(loss)), loss, label="training loss")
plt.plot(np.arange(len(val_loss)), val_loss, label="validation loss")
plt.plot(np.arange(len(triplet_accuracy)), triplet_accuracy, label="triplet_accuracy")
plt.legend()
plt.savefig(model_dir+"/train_loss.png")
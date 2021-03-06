import importlib
import json
import numpy as np
import os
import sys
import time
import uuid
import copy

from hypergan.discriminators import *
from hypergan.distributions import *
from hypergan.generators import *
from hypergan.inputs import *
from hypergan.samplers import *
from hypergan.trainers import *

import hyperchamber as hc
from hyperchamber import Config
from hypergan.ops import TensorflowOps
import tensorflow as tf
import hypergan as hg

from hypergan.gan_component import ValidationException, GANComponent
from .base_gan import BaseGAN

class StandardGAN(BaseGAN):
    """ 
    Standard GANs consist of:
    
    *required to sample*
    
    * latent
    * generator
    * sampler

    *required to train*

    * discriminator
    * loss
    * trainer
    """
    def __init__(self, *args, **kwargs):
        self.discriminator = None
        self.latent = None
        self.generator = None
        self.loss = None
        self.trainer = None
        self.session = None
        BaseGAN.__init__(self, *args, **kwargs)

    def required(self):
        return "generator".split()

    def create(self):
        config = self.config

        with tf.device(self.device):
            if self.session is None: 
                self.session = self.ops.new_session(self.ops_config)

            #this is in a specific order
            if self.latent is None:
                self.latent = self.create_component(config.z_distribution or config.latent)
                self.uniform_distribution = self.latent

            z_shape = self.ops.shape(self.latent.sample)
            self.android_input = tf.reshape(self.latent.sample, [-1])

            direction, slider = self.create_controls(self.ops.shape(self.android_input))
            self.slider = slider
            self.direction = direction
            z = self.android_input + slider * direction
            z = tf.maximum(-1., z)
            z = tf.minimum(1., z)
            z = tf.reshape(z, z_shape)
            self.control_z = z

            if self.generator is None and config.generator:
                self.generator = self.create_component(config.generator, name="generator", input=z)
                self.autoencoded_x = self.generator.sample
                self.uniform_sample = self.generator.sample

            if self.discriminator is None and config.discriminator:
                x, g = self.inputs.x, self.generator.sample
                self.discriminator = self.create_component(config.discriminator, name="discriminator", input=tf.concat([x,g],axis=0))
            if self.loss is None and config.loss:
                self.loss = self.create_component(config.loss, discriminator=self.discriminator)
            if self.trainer is None and config.trainer:
                self.trainer = self.create_component(config.trainer)

            #self.random_z = tf.random_uniform(self.ops.shape(self.latent.sample), -1, 1, name='random_z')
            if hasattr(self.generator, 'sample'):
                self.android_output = tf.reshape(self.generator.sample, [-1])
            else:
                self.android_output = None

            self.session.run(tf.global_variables_initializer())

    def create_controls(self, z_shape):
        direction = tf.constant(0.0, shape=z_shape, name='direction') * 1.00
        slider = tf.constant(0.0, name='slider', dtype=tf.float32) * 1.00
        return direction, slider

    def g_vars(self):
        return self.latent.variables() + self.generator.variables()
    def d_vars(self):
        return self.discriminator.variables()

    def input_nodes(self):
        "used in hypergan build"
        return [
                self.android_input
        ]

    def output_nodes(self):
        "used in hypergan build"
        return [
                self.android_output
        ]

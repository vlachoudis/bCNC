#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

# Traveling Salesman Problem

import sys
import time
import random
from math import sqrt

import Genetic

#==============================================================================
# Traveller Salesman Individual
#==============================================================================
class TSPIndividual(Genetic.Individual):
	matrix = []
	coords = []

	# ----------------------------------------------------------------------
	def makechromosome(self):
		"makes a chromosome from randomly selected alleles."
		self.chromosome = range(len(self))
		for i in range(len(self)):
			self.mutate(i)
		return self.chromosome

	# ----------------------------------------------------------------------
	# swap mutation
	# ----------------------------------------------------------------------
	def mutate(self, gene):
		gene2 = random.randint(0, len(self)-1)
		self.chromosome[gene], self.chromosome[gene2] = self.chromosome[gene2], self.chromosome[gene]

	# --------------------------------------------------------------------
	def crossover(self, other):
		pivot = random.randrange(1,len(self)-1)
		A = self.chromosome[:pivot]	# prefix
		B = other.chromosome[:pivot]	# prefix
		for i in range(pivot, len(self)):
			x = other.chromosome[i]
			if x not in A: A.append(x)
			x = self.chromosome[i]
			if x not in B: B.append(x)
		for i in range(pivot, len(self)):
			x = self.chromosome[i]
			if x not in A: A.append(x)
			x = other.chromosome[i]
			if x not in B: B.append(x)
		return self.__class__(A),self.__class__(B)

	# --------------------------------------------------------------------
	# Every gene should appear only once
	# --------------------------------------------------------------------
	def repair(self, parent1, parent2):
		# Find what is missing
		errors = []
		for i in range(len(self)):
			if i not in self.chromosome:
				errors.append(i)

		for i, x  in enumerate(self.chromosome):
			try:
				j = self.chromosome.index(x,i+1)
				new = random.choice(errors)
				errors.remove(new)
				self.chromosome[j] = new
			except ValueError:
				pass

	# --------------------------------------------------------------------
	def evaluate(self, optimum=None):
		""" The evaluation function """
		total = 0.0
		num_cities=len(self)
		for i in range(num_cities):
			j = (i+1)%num_cities
			city_i = self.chromosome[i]
			city_j = self.chromosome[j]
			total += TSPIndividual.matrix[city_i][city_j]
		return total

	# --------------------------------------------------------------------
	@staticmethod
	def prepareMatrix():
		TSPIndividual.cartesianMatrix()
		n = len(TSPIndividual.coords)
		TSPIndividual.alleles = [Genetic.IntAllele(0,n-1)] * n

	# --------------------------------------------------------------------
	@staticmethod
	def cartesianMatrix():
		""" A distance matrix """
		del TSPIndividual.matrix[:]

		n = len(TSPIndividual.coords)
		for i in range(n):
			TSPIndividual.matrix.append([0.0] * n)
		for i,((dummy),(x1,y1)) in enumerate(TSPIndividual.coords):
			for j,((x2,y2),dummy) in enumerate(TSPIndividual.coords):
				dx = x1-x2
				dy = y1-y2
				TSPIndividual.matrix[i][j] = sqrt(dx*dx + dy*dy)

#!bin/env python
# $Id: Genetic.py 3456 2015-03-04 10:42:14Z bnv $
#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
#
# All rights not expressly granted under this license are reserved.
#
# Installation, use, reproduction, display of the
# software ("flair"), in source and binary forms, are
# permitted free of charge on a non-exclusive basis for
# internal scientific, non-commercial and non-weapon-related
# use by non-profit organizations only.
#
# For commercial use of the software, please contact the main
# author Vasilis.Vlachoudis@cern.ch for further information.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGES.
#
# Part of code from: http://code.activestate.com/recipes/199121-a-simple-genetic-algorithm/
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	23-Jan-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import time
import random
import threading

from log import say
from pprint import pformat
from functools import total_ordering

MINIMIZE = False
MAXIMIZE = True

#===============================================================================
# Fitness value, used for comparison
#===============================================================================
@total_ordering
class Fitness:
	def __init__(self, value):
		self.value = value

	# ----------------------------------------------------------------------
	def __eq__(self, other):
		return self.value == other

	# ----------------------------------------------------------------------
	def __lt__(self, other):
		return self.value < other

	# ----------------------------------------------------------------------
	def __add__(self, other):
		return Fitness(self.value + other.value)

	# ----------------------------------------------------------------------
	def __div__(self, f):
		return Fitness(self.value / f)

	# ----------------------------------------------------------------------
	def clone(self):
		return self.__class__(self.value)

	# ----------------------------------------------------------------------
	def __repr__(self):
		return pformat(self.value)

#===============================================================================
# Base Allele class
#===============================================================================
class Allele:
	tries = 10

	"""Allele base class"""
	# ----------------------------------------------------------------------
	# @return a random value of allele
	# ----------------------------------------------------------------------
	def random(self):
		"""return a random value"""
		raise

	# ----------------------------------------------------------------------
	def mutate(self, old):
		for i in range(self.tries):
			x = self.random()
			if x != old: return x
		return x

#===============================================================================
# Binary Allele class
#===============================================================================
class BinaryAllele(Allele):
	"""Allele base class"""
	# ----------------------------------------------------------------------
	# @return a random value of allele
	# ----------------------------------------------------------------------
	def random(self):
		"""return a random value"""
		return random.choice((0,1))

	# ----------------------------------------------------------------------
	def mutate(self, old):
		return 1-old

#===============================================================================
# Range Allele
#===============================================================================
class RangeAllele(Allele):
	"""Base Range allele class"""
	"""Integer allele class"""
	def __init__(self, _min, _max, step=1):
		self.setRange(_min, _max)
		self.setStep(step)

	# ----------------------------------------------------------------------
	def setRange(self, _min, _max):
		self.min = _min
		self.max = _max

	# ----------------------------------------------------------------------
	def setStep(self, step=1):
		self.step = step

#===============================================================================
# Integer Allele
#===============================================================================
class IntAllele(RangeAllele):
	"""Integer allele class"""
	# ----------------------------------------------------------------------
	def random(self):
		"""return a random value"""
		return random.randint(self.min, self.max)

	# ----------------------------------------------------------------------
	def mutate(self, old):
		for i in range(self.tries):
			s = random.randint(-self.step, self.step)
			if s!=0:
				return old+s
		return old

#===============================================================================
# Real number allele
#===============================================================================
class RealUniformAllele(RangeAllele):
	"""Real number allele class with uniform mutator"""
	# ----------------------------------------------------------------------
	def random(self):
		"""return a random value"""
		return random.uniform(self.min, self.max)

	# ----------------------------------------------------------------------
	def mutate(self, old):
		for i in range(self.tries):
			s = random.uniform(-self.step, self.step)
			if s!=0.0:
				return old+s
		return old

#===============================================================================
# Real number allele
#===============================================================================
class RealGaussAllele(RangeAllele):
	"""Real number allele with Gaussian mutator"""

	# ----------------------------------------------------------------------
	def random(self):
		"""return a random value"""
		x = random.gauss((self.min+self.max)/2.0, self.step)
		if   x<self.min: return self.min
		elif x>self.max: return self.max
		else:
			return x

	# ----------------------------------------------------------------------
	def mutate(self, old):
		for i in range(self.tries):
			s = random.gauss(0.0, self.step)
			if s!=0.0:
				return old+s
		return old

#===============================================================================
# Allele from a list of choices
#===============================================================================
class ListAllele(Allele):
	"""List allele class"""
	def __init__(self, choices, step=None):
		self.choices = choices
		self.step = step

	# ----------------------------------------------------------------------
	# Return limits of allele
	# ----------------------------------------------------------------------
	def choices(self):
		"""return minimum limit of allele"""
		return self.choices

	# ----------------------------------------------------------------------
	def random(self):
		"""return a random value"""
		return random.choice(self.choices)

	# ----------------------------------------------------------------------
	def mutate(self, old):
		if self.step is None:
			return Allele.mutate(old)
		else:
			idx = self.choices.index(old)
			for i in range(self.tries):
				s = random.randint(-self.step, self.step)
				if s!=0:
					new = idx + s
					if 0 <= new < len(self.choices):
						return self.choices[new]
			return old

#===============================================================================
# Individual Gene
#===============================================================================
@total_ordering
class Individual(threading.Thread):
	alleles       = []		# list of instances of allele classes
	fitness_class = Fitness		# fitness class used for score
	seperator     = ','		# separator for printing
	optimization  = MINIMIZE

	# ----------------------------------------------------------------------
	def __init__(self, chromosome=None):
		threading.Thread.__init__(self)
		self.chromosome = chromosome or self.makechromosome()
		self.score = None  # set during evaluation

	# ----------------------------------------------------------------------
	# List operations
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.alleles)
	def __getitem__(self, i):
		return self.chromosome[i]
	def __setitem__(self, i, value):
		self.chromosome[i] = value
	def append(self, x):
		self.chromosome.append(x)
	def extend(self, x):
		self.chromosome.extend(x)

	# ----------------------------------------------------------------------
	def makechromosome(self):
		"makes a chromosome from randomly selected alleles."
		chromosome = []
		for allele in self.alleles:
			chromosome.append(allele.random())
		return chromosome

	# ----------------------------------------------------------------------
	def run(self, optimum=None):
		self.score = self.fitness_class(self.evaluate(optimum))

	# ----------------------------------------------------------------------
	# Must return a Fitness() variable to set to the self.score
	# ----------------------------------------------------------------------
	def evaluate(self, optimum=None):
		"this method MUST be overridden to evaluate individual fitness score."
		pass

	# ----------------------------------------------------------------------
	def crossover(self, other):
		"override this method to use your preferred crossover method."
		return self._twopoint(other)

	# ----------------------------------------------------------------------
	# single point cross over
	# ----------------------------------------------------------------------
	def _singlepoint(self, other):
		pivot = random.randrange(1,len(self)-1)
		return self.__class__(self.chromosome[:pivot]  + other.chromosome[pivot:]), \
		       self.__class__(other.chromosome[:pivot] + self.chromosome[pivot:])

	# ----------------------------------------------------------------------
	# two point crossover method
	# ----------------------------------------------------------------------
	def _twopoint(self, other):
		"creates offspring via two-point crossover between mates."
		left, right = self._pickpivots()
		def mate(p0, p1):
			chromosome = p0.chromosome[:]
			chromosome[left:right] = p1.chromosome[left:right]
			child = p0.__class__(chromosome)
			child.repair(p0, p1)
			return child
		return mate(self, other), mate(other, self)

	# ----------------------------------------------------------------------
	def _pickpivots(self):
		left  = random.randrange(1, len(self)-2)
		right = random.randrange(left, len(self)-1)
		return left, right

	# ----------------------------------------------------------------------
	# some crossover helpers ...
	# ----------------------------------------------------------------------
	def repair(self, parent1, parent2):
		"override this method, if necessary, to fix duplicated genes."
		pass

	# ----------------------------------------------------------------------
	# sample mutation method
	# ----------------------------------------------------------------------
	def mutate(self, gene):
		"override this method to use your preferred mutation method."
		self.chromosome[gene] = self.alleles[gene].mutate(self.chromosome[gene])

	# ----------------------------------------------------------------------
	# other methods
	# ----------------------------------------------------------------------
	def clone(self):
		twin = self.__class__(self.chromosome[:])
		twin.score = self.score.clone()
		return twin

	# ----------------------------------------------------------------------
	# @return true if two individuals are the same
	# WARNING: this is different from __eq__ which tests if their score is
	#          equal
	# ----------------------------------------------------------------------
	def same(self, other):
		return self.chromosome == other.chromosome
#		for a,b in zip(self.chromosome, other.chromosome):
#			if a != b: return False
#		return True

	# ----------------------------------------------------------------------
	def __eq__(self, other):
		return self.score == other.score

	# ----------------------------------------------------------------------
	def __lt__(self, other):
#		if self.optimization == MINIMIZE:
			return self.score < other.score
#		else: # MAXIMIZE
#			return other.score < self.score

	# ----------------------------------------------------------------------
	def __repr__(self):
		"returns string representation of self"
		return '<%s chromosome="%s" score=%s>' % \
			(self.__class__.__name__,
			self.seperator.join(map(str,self.chromosome)), str(self.score))

#===============================================================================
# Running Environment
#===============================================================================
class Environment:
	# ----------------------------------------------------------------------
	def __init__(self, kind, population=None, size=100, maxgenerations=100,
			 crossover_rate=0.90, mutation_rate=0.01, optimum=None,
			 parallel=0, sleep=0.01):

		self.kind       = kind
		self.size       = size
		self.optimum    = optimum
		self.parallel   = parallel
		self.sleep      = sleep
		self.population = population or self._makepopulation()
		self.generation = 0
		self.callback   = None
		self.elitism    = 1
		self.random     = 0
		self._report    = 10
		self._oldreport = 0
		self._startTime = 0
		self._prevTime  = 0

		self.crossover_rate = crossover_rate
		self.mutation_rate  = mutation_rate
		self.maxgenerations = maxgenerations

	# ----------------------------------------------------------------------
	def _makepopulation(self):
		return [self.kind() for individual in range(self.size)]

	# ----------------------------------------------------------------------
	def reportEvery(self, every):
		self._report = every

	# ----------------------------------------------------------------------
	def run(self):
		self._startTime = self._prevTime= time.time()

		# Evaluate all individuals
		for individual in self.population:
			self._evaluate(individual)
		# Wait for all individuals to finish
		self._wait(self.population)

		# call callback
		if self.callback: self.callback(self)

		# Loop until goal is reached
		while not self._goal():
			self._prevTime= time.time()
			self.step()
			if self.callback: self.callback(self)

		self.report()

	# ----------------------------------------------------------------------
	def step(self):
		self.population.sort()
		if self.generation - self._oldreport == self._report:
			self._oldreport = self.generation
			self.report()
		self.generation += 1
		self._crossover()

	# ----------------------------------------------------------------------
	def _goal(self):
		if self.optimum is None:
			return self.generation > self.maxgenerations

		if self.kind.optimization == MINIMIZE:
			return self.generation > self.maxgenerations or \
				self.best().score <= self.optimum
		else:
			return self.generation > self.maxgenerations or \
				self.best().score >= self.optimum

	# ----------------------------------------------------------------------
	# Crossover of population
	# ----------------------------------------------------------------------
	def _crossover(self):
		# Keep the best ones
		next_population = self.population[:self.elitism]

		# Make a few random individuals
		for i in range(self.random):
			individual = self.kind()
			#self._evaluate(individual)
			next_population.append(individual)

		# Mate and mutate
		while len(next_population) < self.size:
			mate1 = self.select()
			if random.random() < self.crossover_rate:
				mate2 = self.select()
				offspring = mate1.crossover(mate2)
			else:
				offspring = [mate1.clone()]

			for individual in offspring:
				if len(next_population) == self.size: break
				self._mutate(individual)
				#self._evaluate(individual)
				next_population.append(individual)

		# Mutate a bit more duplicate individuals to make them unique
		#dups = 0
		for i,a in enumerate(next_population):
			for b in next_population[i+1:]:
				for j in range(100):	# avoid infinite loop
					if not a.same(b): break
					#dups += 1
					self._mutate(b) # mutate until different

		# Evaluate the new individuals
		for individual in next_population[self.elitism:]:
			self._evaluate(individual)
		self._wait(next_population)

		# Transfer to population
		self.population = next_population[:self.size]

	# ----------------------------------------------------------------------
	# Evaluate individual
	# ----------------------------------------------------------------------
	def _evaluate(self, individual):
		if self.parallel:
			#print threading.activeCount()
			while threading.activeCount() > self.parallel:
				time.sleep(self.sleep)
			# Spawn thread
			individual.start()
		else:
			individual.run(self.optimum)

	# ----------------------------------------------------------------------
	# Wait for all individuals to finish
	# ----------------------------------------------------------------------
	def _wait(self, population):
		if self.parallel:
			# Wait until all individual finished evaluation
			for individual in population[1:]:
				if individual.isAlive():
					individual.join()

	# ----------------------------------------------------------------------
	def select(self):
		"override this to use your preferred selection method"
		return self._tournament()

	# ----------------------------------------------------------------------
	# tournament selection method
	# ----------------------------------------------------------------------
	def _tournament(self, size=8, choosebest=0.90):
		competitors = [random.choice(self.population) for i in range(size)]
		competitors.sort()
		if random.random() < choosebest:
			return competitors[0]
		else:
			return random.choice(competitors[1:])

	# ----------------------------------------------------------------------
	# Parents are selected according to their fitness. The better the
	# chromosomes are, the more chances to be selected they have. Imagine a
	# roulette wheel where are placed all chromosomes in the population,
	# every has its place big accordingly to its fitness function, like on
	# the following picture.
	#
	# [Sum]    Calculate sum of all chromosome fitnesses in population - sum S.
	# [Select] Generate random number from interval (0,S) - r.
	# [Loop]   Go through the population and sum fitnesses from 0 - sum s.
	#          When the sum s is greater then r, stop and return the chromosome
	#          where you are.
	# ----------------------------------------------------------------------
	#def _rouletteSelection(self):
	#	pass

	# ----------------------------------------------------------------------
	# rank selection
	# Rank selection first ranks the population and then every chromosome
	# receives fitness from this ranking. The worst will have fitness 1,
	# second worst 2 etc. and the best will have fitness N (number of
	# chromosomes in population).
	# ----------------------------------------------------------------------
	def _rankSelection(self):
		n = len(self.population)
		rnd = random.randint(1,(n*(n+1))//2)
		lower = 0
		upper = n-1
		while upper>=lower:
			mid = (lower + upper) // 2
			if (mid*(mid+1))//2 >= rnd:
				upper = mid - 1
			else:
				lower = mid + 1
		return self.population[n-lower]	# 0=maximum

	# ----------------------------------------------------------------------
	# _wheel selection with a fitness_ in the 
	# @return index of item selected
	# ----------------------------------------------------------------------
	#def _wheel(self, fitness_):
	#

	# ----------------------------------------------------------------------
	def _mutate(self, individual):
		for gene in range(len(individual)):
			if random.random() < self.mutation_rate:
				individual.mutate(gene)

	# ----------------------------------------------------------------------
	# individual with best fitness score in population.
	# ----------------------------------------------------------------------
	def best(self): return self.population[0]

	# ----------------------------------------------------------------------
	def min(self): return min(x.score for x in self.population)
	def max(self): return max(x.score for x in self.population)
	def sum(self): return reduce((lambda x,y:x+y), [x.score for x in self.population])
	def avg(self): return self.sum() / float(len(self.population))

	# ----------------------------------------------------------------------
	def report(self):
		say("="*70)
		say("Gen: %d  Min/Avg/Max  %s / %s / %s" % \
			(self.generation, str(self.min()),
			 str(self.avg()), str(self.max())))
		say("Best: %s"%(str(self.best())))
		say("Time: %g"%(time.time()-self._prevTime))

#-------------------------------------------------------------------------------
if __name__ == "__main__":
	class OneMax(Individual):
		optimization = MAXIMIZE
		alleles = [BinaryAllele()]*30

		# --------------------------------------------------------------
		def evaluate(self, optimum=None):
			return sum(self.chromosome)

	env = Environment(OneMax, maxgenerations=100, optimum=30, parallel=8)
	env.reportEvery(1)
	env.run()

#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

__all__ = ["ConstrainedGaussianRandomWalk", "GaussianRandomWalk"]

import random

class ConstrainedGaussianRandomWalk(object):
    """A constrained random walk generator with a gaussian deviation at each step
    """
    def __init__(self, homeValue, sigma, minValue, maxValue):
        """
        Inputs:
        - minValue, maxValue: allowed limits for value
        - homeValue: value the random value is drawn to
        - sigma: standard deviation of random gaussian distribution
        """
        self.homeValue = float(homeValue)
        self.sigma = float(sigma)
        self.minValue = float(minValue)
        self.maxValue = float(maxValue)
        self.value = self.homeValue
        if not self.minValue <= self.homeValue <= self.maxValue:
            raise RuntimeError("Need min=%s <= home=%s <= max=%s" % (self.minValue, self.homeValue, self.maxValue))

    def __iter__(self):
        return self
    
    def next(self):
        """Randomly change the value and return the next value
        """
        rawDelta = random.gauss(0, self.sigma)
        proposedValue = self.value + rawDelta

        if proposedValue > self.homeValue:
            probOfFlip = (proposedValue - self.homeValue) / (self.maxValue - self.homeValue)
        else:
            probOfFlip = (self.homeValue - proposedValue) / (self.homeValue - self.minValue)

        if random.random() < probOfFlip:
            self.value -= rawDelta
        else:
            self.value = proposedValue
        self.value = min(max(self.value, self.minValue), self.maxValue)
        return self.value

class GaussianRandomWalk(object):
    """An random walk generator with gaussian deviation
    """
    def __init__(self, initialValue, sigma):
        """
        Inputs:
        - initialValue: starting value
        - sigma: standard deviation of random gaussian distribution
        """
        self.value = float(initialValue)
        self.sigma = float(sigma)

    def __iter__(self):
        return self
    
    def next(self):
        """Randomly change the value and return the new value
        """
        self.value += random.gauss(0, self.sigma)
        return self.value

if __name__ == "__main__":
    grw = GaussianRandomWalk(5, 2)
    cgrw = ConstrainedGaussianRandomWalk(0, 2, -1, 15)
    print("gauss   constr")
    for i in range(100):
        print(("%8.2f %8.2f" % (next(grw), next(cgrw))))

class Customer:
    def __init__(self, id, x, y, demand):
        self.id = id
        self.x = x
        self.y = y
        self.demand = demand


class Vehicle:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity


class Route:
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.customers = []

    def add_customer(self, customer):
        self.customers.append(customer)


class Solution:
    def __init__(self):
        self.routes = []

    def add_route(self, route):
        self.routes.append(route)
class Customer:
    def __init__(self, id, x, y, demand):
        self.id = id
        self.x = x
        self.y = y
        self.demand = demand


class Vehicle:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity


class Route:
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.customers = []

    def add_customer(self, customer):
        self.customers.append(customer)


class Solution:
    def __init__(self):
        self.routes = []

    def add_route(self, route):
        self.routes.append(route)
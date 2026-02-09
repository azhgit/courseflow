# Python Classes and Object-Oriented Programming

## What is Object-Oriented Programming?

Object-Oriented Programming (OOP) is a programming paradigm that organizes code around objects that contain both data (attributes) and code (methods). Python fully supports OOP, making it easy to create reusable, modular code.

## Classes and Objects

### Defining a Class

A class is a blueprint for creating objects:

```python
class Dog:
    """A simple class representing a dog."""
    
    def __init__(self, name, age):
        """Initialize dog attributes."""
        self.name = name
        self.age = age
    
    def bark(self):
        """Simulate a dog barking."""
        return f"{self.name} says Woof!"
```

### Creating Objects (Instances)

```python
# Create instances of the Dog class
my_dog = Dog("Buddy", 3)
your_dog = Dog("Lucy", 5)

# Access attributes
print(my_dog.name)  # Output: Buddy
print(your_dog.age)  # Output: 5

# Call methods
print(my_dog.bark())  # Output: Buddy says Woof!
```

## The __init__ Method

The `__init__` method is a special constructor method automatically called when an object is created:

```python
class Person:
    def __init__(self, name, age):
        self.name = name  # Instance attribute
        self.age = age
```

## Class vs Instance Attributes

### Instance Attributes
Unique to each object:

```python
class Car:
    def __init__(self, make, model):
        self.make = make    # Instance attribute
        self.model = model  # Instance attribute
```

### Class Attributes
Shared by all instances:

```python
class Car:
    wheels = 4  # Class attribute (shared by all cars)
    
    def __init__(self, make, model):
        self.make = make
        self.model = model

car1 = Car("Toyota", "Camry")
car2 = Car("Honda", "Civic")

print(car1.wheels)  # 4
print(car2.wheels)  # 4
print(Car.wheels)   # 4 (access via class)
```

## Methods

### Instance Methods
Operate on instance data (use `self`):

```python
class Circle:
    def __init__(self, radius):
        self.radius = radius
    
    def area(self):
        return 3.14159 * self.radius ** 2
    
    def circumference(self):
        return 2 * 3.14159 * self.radius

circle = Circle(5)
print(circle.area())  # 78.53975
```

### Class Methods
Operate on class data (use `cls`):

```python
class Employee:
    raise_amount = 1.04  # Class attribute
    
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary
    
    @classmethod
    def set_raise_amount(cls, amount):
        cls.raise_amount = amount

Employee.set_raise_amount(1.05)
```

### Static Methods
Don't access instance or class data:

```python
class Math:
    @staticmethod
    def add(x, y):
        return x + y
    
    @staticmethod
    def multiply(x, y):
        return x * y

print(Math.add(5, 3))  # 8
```

## Inheritance

Classes can inherit from other classes:

```python
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return f"{self.name} says Woof!"

class Cat(Animal):
    def speak(self):
        return f"{self.name} says Meow!"

dog = Dog("Buddy")
cat = Cat("Whiskers")

print(dog.speak())  # Buddy says Woof!
print(cat.speak())  # Whiskers says Meow!
```

### The super() Function

Access parent class methods:

```python
class Animal:
    def __init__(self, name, species):
        self.name = name
        self.species = species

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name, "Canine")
        self.breed = breed

dog = Dog("Buddy", "Golden Retriever")
print(dog.species)  # Canine
```

## Encapsulation

### Public, Protected, and Private Attributes

```python
class BankAccount:
    def __init__(self, balance):
        self.public_attr = "accessible anywhere"
        self._protected_attr = "intended for internal use"
        self.__private_attr = balance  # Name mangling
    
    def get_balance(self):
        return self.__private_attr
    
    def deposit(self, amount):
        if amount > 0:
            self.__private_attr += amount

account = BankAccount(1000)
print(account.public_attr)        # OK
print(account._protected_attr)    # Works but discouraged
# print(account.__private_attr)   # AttributeError
print(account.get_balance())      # Use getter method
```

## Properties

Use properties for controlled attribute access:

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius
    
    @property
    def celsius(self):
        return self._celsius
    
    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("Temperature below absolute zero")
        self._celsius = value
    
    @property
    def fahrenheit(self):
        return (self.celsius * 9/5) + 32

temp = Temperature(25)
print(temp.celsius)      # 25
print(temp.fahrenheit)   # 77.0
temp.celsius = 30        # Uses setter
```

## Magic Methods (Dunder Methods)

Special methods that start and end with double underscores:

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __str__(self):
        """String representation for users"""
        return f"Point({self.x}, {self.y})"
    
    def __repr__(self):
        """String representation for developers"""
        return f"Point(x={self.x}, y={self.y})"
    
    def __add__(self, other):
        """Define addition for Point objects"""
        return Point(self.x + other.x, self.y + other.y)
    
    def __eq__(self, other):
        """Define equality for Point objects"""
        return self.x == other.x and self.y == other.y

p1 = Point(1, 2)
p2 = Point(3, 4)

print(p1)           # Point(1, 2)
p3 = p1 + p2        # Uses __add__
print(p3)           # Point(4, 6)
print(p1 == p2)     # False (uses __eq__)
```

### Common Magic Methods

- `__init__`: Constructor
- `__str__`: String representation (str())
- `__repr__`: Official representation (repr())
- `__len__`: Length (len())
- `__getitem__`: Indexing ([])
- `__add__`: Addition (+)
- `__eq__`: Equality (==)
- `__lt__`: Less than (<)

## Polymorphism

Objects of different classes can be used interchangeably:

```python
class Dog:
    def speak(self):
        return "Woof!"

class Cat:
    def speak(self):
        return "Meow!"

class Duck:
    def speak(self):
        return "Quack!"

def animal_sound(animal):
    print(animal.speak())

animals = [Dog(), Cat(), Duck()]
for animal in animals:
    animal_sound(animal)
# Output: Woof! Meow! Quack!
```

## Abstract Base Classes

Define interfaces that subclasses must implement:

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        pass
    
    @abstractmethod
    def perimeter(self):
        pass

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def area(self):
        return self.width * self.height
    
    def perimeter(self):
        return 2 * (self.width + self.height)

# shape = Shape()  # TypeError: Can't instantiate abstract class
rect = Rectangle(5, 3)
print(rect.area())  # 15
```

## Best Practices

1. **Use meaningful class names**: Classes should be nouns (e.g., `User`, `Product`)
2. **Keep classes focused**: Each class should have a single, well-defined purpose
3. **Use inheritance wisely**: Prefer composition over inheritance when possible
4. **Encapsulate data**: Use properties for controlled access
5. **Document classes**: Use docstrings to explain purpose and usage
6. **Follow naming conventions**: 
   - Class names: PascalCase (e.g., `MyClass`)
   - Method/attribute names: snake_case (e.g., `my_method`)
7. **Use `__str__` and `__repr__`**: Make objects easy to debug and print

## Common Patterns

### Singleton Pattern

```python
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Factory Pattern

```python
class ShapeFactory:
    @staticmethod
    def create_shape(shape_type):
        if shape_type == "circle":
            return Circle()
        elif shape_type == "square":
            return Square()
```

Object-oriented programming in Python provides powerful tools for organizing code, promoting reusability, and modeling real-world concepts effectively.

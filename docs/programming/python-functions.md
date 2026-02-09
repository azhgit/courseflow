# Python Functions: A Comprehensive Guide

## What are Functions?

Functions are reusable blocks of code that perform a specific task. They help organize code, reduce repetition, and make programs more modular and maintainable.

## Basic Function Syntax

### Defining a Function

Use the `def` keyword to define a function:

```python
def greet():
    print("Hello, World!")

# Call the function
greet()  # Output: Hello, World!
```

### Functions with Parameters

Functions can accept input values called parameters:

```python
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")  # Output: Hello, Alice!
```

### Multiple Parameters

Functions can have multiple parameters:

```python
def add(a, b):
    return a + b

result = add(5, 3)
print(result)  # Output: 8
```

## Return Values

Functions can return values using the `return` keyword:

```python
def square(x):
    return x * x

result = square(4)
print(result)  # Output: 16
```

Functions without an explicit return statement return `None`:

```python
def no_return():
    print("This function returns None")

result = no_return()
print(result)  # Output: None
```

## Parameter Types

### Default Parameters

Provide default values for parameters:

```python
def greet(name="World"):
    print(f"Hello, {name}!")

greet()         # Output: Hello, World!
greet("Bob")    # Output: Hello, Bob!
```

### Keyword Arguments

Call functions using parameter names:

```python
def describe_pet(animal, name):
    print(f"I have a {animal} named {name}")

describe_pet(animal="dog", name="Rex")
describe_pet(name="Whiskers", animal="cat")  # Order doesn't matter
```

### Arbitrary Arguments (*args)

Accept any number of positional arguments:

```python
def sum_all(*numbers):
    total = 0
    for num in numbers:
        total += num
    return total

print(sum_all(1, 2, 3))        # Output: 6
print(sum_all(1, 2, 3, 4, 5))  # Output: 15
```

### Arbitrary Keyword Arguments (**kwargs)

Accept any number of keyword arguments:

```python
def print_info(**info):
    for key, value in info.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=30, city="New York")
```

## Function Scope

Variables defined inside a function have local scope:

```python
def my_function():
    x = 10  # Local variable
    print(x)

my_function()  # Output: 10
# print(x)     # Error: x is not defined outside the function
```

### Global Variables

Use the `global` keyword to modify global variables:

```python
count = 0

def increment():
    global count
    count += 1

increment()
print(count)  # Output: 1
```

## Lambda Functions

Anonymous, one-line functions:

```python
# Regular function
def square(x):
    return x * x

# Lambda equivalent
square = lambda x: x * x

print(square(5))  # Output: 25

# Common use: with map, filter, sorted
numbers = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x * x, numbers))
print(squared)  # Output: [1, 4, 9, 16, 25]
```

## Docstrings

Document functions using docstrings:

```python
def calculate_area(radius):
    """
    Calculate the area of a circle.
    
    Args:
        radius: The radius of the circle
        
    Returns:
        The area of the circle (float)
    """
    return 3.14159 * radius * radius

print(calculate_area.__doc__)  # Prints the docstring
help(calculate_area)            # Shows documentation
```

## Type Hints

Add type annotations for better code clarity (Python 3.5+):

```python
def add(a: int, b: int) -> int:
    """Add two integers and return the result."""
    return a + b

def greet(name: str) -> None:
    """Print a greeting message."""
    print(f"Hello, {name}!")
```

## Nested Functions

Define functions inside other functions:

```python
def outer_function(text):
    def inner_function():
        print(text)
    
    inner_function()

outer_function("Hello from inner function!")
```

## Closures

Inner functions can access variables from outer functions:

```python
def make_multiplier(n):
    def multiplier(x):
        return x * n
    return multiplier

times3 = make_multiplier(3)
print(times3(10))  # Output: 30
```

## Decorators

Functions that modify other functions:

```python
def uppercase_decorator(func):
    def wrapper():
        result = func()
        return result.upper()
    return wrapper

@uppercase_decorator
def greet():
    return "hello, world!"

print(greet())  # Output: HELLO, WORLD!
```

## Best Practices

1. **Use descriptive names**: Function names should clearly indicate what they do
2. **Keep functions small**: Each function should do one thing well
3. **Add docstrings**: Document what the function does, its parameters, and return value
4. **Use type hints**: Make code more readable and catch type errors early
5. **Avoid side effects**: Functions should be predictable and not modify global state
6. **Return early**: Use guard clauses to handle edge cases first
7. **DRY principle**: Don't Repeat Yourself - create functions for repeated code

## Common Patterns

### Guard Clauses

Handle edge cases early:

```python
def divide(a, b):
    if b == 0:
        return "Cannot divide by zero"
    return a / b
```

### Factory Functions

Functions that create and return objects:

```python
def create_person(name, age):
    return {
        "name": name,
        "age": age,
        "greet": lambda: f"Hi, I'm {name}"
    }

person = create_person("Alice", 30)
print(person["greet"]())  # Output: Hi, I'm Alice
```

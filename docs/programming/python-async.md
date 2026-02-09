# Python Async/Await: Asynchronous Programming Guide

## What is Asynchronous Programming?

Asynchronous programming is a programming paradigm that allows a program to handle multiple tasks concurrently without waiting for each task to complete before moving on to the next. In Python, this is achieved using the `async` and `await` keywords introduced in Python 3.5.

## Why Use Async/Await?

Traditional synchronous code executes one line at a time, blocking on I/O operations like:
- Network requests (API calls, database queries)
- File operations
- Sleep/delay operations

Async programming allows other code to run while waiting for these I/O operations, making programs more efficient, especially for I/O-bound tasks.

## Basic Syntax

### Defining Async Functions

Use the `async def` syntax to define a coroutine function:

```python
async def fetch_data():
    # This is a coroutine function
    return "data"
```

### Calling Async Functions with await

You can only use `await` inside async functions:

```python
async def main():
    result = await fetch_data()
    print(result)
```

The `await` keyword pauses the execution of the async function until the awaited coroutine completes, but it doesn't block the entire program.

## Running Async Code

### Using asyncio.run()

The `asyncio.run()` function is the entry point for running async programs:

```python
import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

# Run the async function
asyncio.run(main())
```

### Creating Tasks

Tasks allow multiple coroutines to run concurrently:

```python
import asyncio

async def task1():
    await asyncio.sleep(2)
    print("Task 1 complete")

async def task2():
    await asyncio.sleep(1)
    print("Task 2 complete")

async def main():
    # Create tasks to run concurrently
    t1 = asyncio.create_task(task1())
    t2 = asyncio.create_task(task2())
    
    # Wait for both to complete
    await t1
    await t2

asyncio.run(main())
```

## Common Patterns

### Gathering Multiple Operations

Use `asyncio.gather()` to run multiple coroutines concurrently and wait for all to complete:

```python
async def main():
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3")
    )
    print(results)  # List of all results
```

### Timeout Handling

Use `asyncio.wait_for()` to set a timeout on operations:

```python
async def main():
    try:
        result = await asyncio.wait_for(slow_operation(), timeout=5.0)
    except asyncio.TimeoutError:
        print("Operation took too long!")
```

### Error Handling

Use try/except blocks as usual:

```python
async def main():
    try:
        result = await risky_operation()
    except Exception as e:
        print(f"Error: {e}")
```

## Real-World Example: Async HTTP Requests

```python
import asyncio
import httpx

async def fetch_url(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

async def main():
    urls = [
        "https://api.example.com/data1",
        "https://api.example.com/data2",
        "https://api.example.com/data3"
    ]
    
    # Fetch all URLs concurrently
    results = await asyncio.gather(*[fetch_url(url) for url in urls])
    
    for i, result in enumerate(results):
        print(f"Result {i}: {result[:100]}...")

asyncio.run(main())
```

## Important Concepts

### Coroutines
Functions defined with `async def` that can be paused and resumed. They return coroutine objects when called.

### Event Loop
The core of asyncio that manages and executes async tasks. `asyncio.run()` creates and manages the event loop automatically.

### Awaitable Objects
Objects that can be used with `await`: coroutines, Tasks, and Futures.

## Common Pitfalls

1. **Forgetting await**: Calling an async function without `await` returns a coroutine object, not the result
2. **Mixing sync and async**: Blocking operations in async code defeats the purpose
3. **Not running in event loop**: Top-level async code must be run with `asyncio.run()`

## Best Practices

1. Use async for I/O-bound operations, not CPU-bound tasks
2. Always `await` coroutines to avoid warnings and bugs
3. Use `asyncio.gather()` for concurrent operations
4. Handle exceptions properly
5. Use `async with` for async context managers
6. Consider using async libraries (httpx, aiohttp, aiosqlite) instead of sync versions

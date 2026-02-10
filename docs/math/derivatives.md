# Calculus: Derivatives and Their Applications

## What are Derivatives?

A derivative represents the rate of change of a function with respect to a variable. In geometric terms, it represents the slope of the tangent line to a curve at a given point. Derivatives are fundamental to calculus and have wide applications in physics, engineering, economics, and many other fields.

## Notation

The derivative of a function f(x) can be written in several ways:
- **Leibniz notation**: df/dx or dy/dx
- **Lagrange notation**: f'(x) or y'
- **Newton notation**: ẋ (used primarily in physics)

## Definition

The derivative of f(x) at point x is defined as:

f'(x) = lim[h→0] (f(x+h) - f(x))/h

This represents the instantaneous rate of change at point x.

## Basic Differentiation Rules

### Power Rule
If f(x) = x^n, then f'(x) = nx^(n-1)

Examples:
- f(x) = x³ → f'(x) = 3x²
- f(x) = x⁵ → f'(x) = 5x⁴
- f(x) = x → f'(x) = 1

### Constant Rule
If f(x) = c (where c is a constant), then f'(x) = 0

### Constant Multiple Rule
If f(x) = c·g(x), then f'(x) = c·g'(x)

Example: f(x) = 5x³ → f'(x) = 5(3x²) = 15x²

### Sum Rule
If f(x) = g(x) + h(x), then f'(x) = g'(x) + h'(x)

Example: f(x) = x³ + 2x² → f'(x) = 3x² + 4x

### Product Rule
If f(x) = g(x)·h(x), then f'(x) = g'(x)·h(x) + g(x)·h'(x)

Example: f(x) = x²·sin(x)
f'(x) = 2x·sin(x) + x²·cos(x)

### Quotient Rule
If f(x) = g(x)/h(x), then f'(x) = [g'(x)·h(x) - g(x)·h'(x)]/[h(x)]²

Example: f(x) = x²/(x+1)
f'(x) = [2x(x+1) - x²(1)]/(x+1)² = (x² + 2x)/(x+1)²

### Chain Rule
If f(x) = g(h(x)), then f'(x) = g'(h(x))·h'(x)

Example: f(x) = (x² + 1)³
Let u = x² + 1, then f = u³
f'(x) = 3u²·2x = 3(x² + 1)²·2x = 6x(x² + 1)²

## Common Derivatives

### Trigonometric Functions
- d/dx[sin(x)] = cos(x)
- d/dx[cos(x)] = -sin(x)
- d/dx[tan(x)] = sec²(x)

### Exponential Functions
- d/dx[e^x] = e^x
- d/dx[a^x] = a^x·ln(a)

### Logarithmic Functions
- d/dx[ln(x)] = 1/x
- d/dx[log_a(x)] = 1/(x·ln(a))

## Applications of Derivatives

### Finding Slopes
The derivative at a point gives the slope of the tangent line at that point.

Example: For f(x) = x², find the slope at x = 3
f'(x) = 2x
f'(3) = 2(3) = 6
The slope of the tangent line at x = 3 is 6.

### Velocity and Acceleration
If s(t) represents position as a function of time:
- **Velocity**: v(t) = s'(t) (first derivative of position)
- **Acceleration**: a(t) = v'(t) = s''(t) (second derivative of position)

### Optimization Problems
Derivatives help find maximum and minimum values:
1. Find f'(x)
2. Set f'(x) = 0 and solve for x (critical points)
3. Use second derivative test: f''(x) > 0 → minimum, f''(x) < 0 → maximum

Example: Maximize the area of a rectangle with perimeter 20
Let x = length, then width = 10 - x
Area A(x) = x(10-x) = 10x - x²
A'(x) = 10 - 2x
Set A'(x) = 0: 10 - 2x = 0 → x = 5
A''(x) = -2 < 0, so x = 5 gives maximum area

### Related Rates
Finding how related quantities change with respect to time.

Example: A balloon is being inflated. If the radius increases at 2 cm/s, how fast is the volume increasing when r = 5 cm?
V = (4/3)πr³
dV/dt = 4πr²·(dr/dt)
When r = 5 and dr/dt = 2:
dV/dt = 4π(5)²(2) = 200π cm³/s

### Curve Sketching
Derivatives help understand function behavior:
- **First derivative**: Indicates increasing (f' > 0) or decreasing (f' < 0)
- **Second derivative**: Indicates concavity (f'' > 0 → concave up, f'' < 0 → concave down)
- **Inflection points**: Where f''(x) = 0 and concavity changes

## Higher-Order Derivatives

### Second Derivative: f''(x) or d²y/dx²
The derivative of the first derivative.

### Third Derivative: f'''(x) or d³y/dx³
And so on...

Example: f(x) = x⁴
- f'(x) = 4x³
- f''(x) = 12x²
- f'''(x) = 24x
- f''''(x) = 24

## Implicit Differentiation

Used when a function is not explicitly solved for y.

Example: Find dy/dx for x² + y² = 25
Differentiate both sides with respect to x:
2x + 2y(dy/dx) = 0
dy/dx = -x/y

## L'Hôpital's Rule

For evaluating limits of indeterminate forms (0/0 or ∞/∞):
If lim[x→a] f(x)/g(x) is indeterminate, then:
lim[x→a] f(x)/g(x) = lim[x→a] f'(x)/g'(x)

Example: lim[x→0] sin(x)/x
Using L'Hôpital's: lim[x→0] cos(x)/1 = 1

## Common Mistakes

1. Forgetting to use the chain rule
2. Confusing product rule with simple multiplication
3. Sign errors in quotient rule
4. Not simplifying final answers
5. Forgetting that the derivative of a constant is zero

## Practice Tips

1. Master the basic rules before moving to complex problems
2. Always check your work by looking at special cases
3. Practice recognizing when to use each rule
4. Simplify expressions before differentiating when possible
5. Verify answers using numerical approximations when possible

Derivatives are powerful tools that unlock understanding of change and optimization. Mastering them opens doors to advanced mathematics, physics, and engineering applications.

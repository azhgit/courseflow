# Linear Algebra: Matrices and Their Operations

## What are Matrices?

A matrix is a rectangular array of numbers, symbols, or expressions arranged in rows and columns. Matrices are fundamental in linear algebra and have applications in computer graphics, physics, engineering, economics, and data science.

## Matrix Notation

A matrix is typically denoted with a capital letter. For example:

```
A = [a₁₁  a₁₂  a₁₃]
    [a₂₁  a₂₂  a₂₃]
```

This is a 2×3 matrix (2 rows, 3 columns).

## Types of Matrices

### Square Matrix
A matrix with the same number of rows and columns (n×n).

```
[1  2  3]
[4  5  6]
[7  8  9]
```

### Row Matrix
A matrix with only one row (1×n).

```
[1  2  3  4]
```

### Column Matrix (Vector)
A matrix with only one column (n×1).

```
[1]
[2]
[3]
```

### Identity Matrix
A square matrix with 1s on the diagonal and 0s elsewhere.

```
I₃ = [1  0  0]
     [0  1  0]
     [0  0  1]
```

### Zero Matrix
A matrix where all elements are zero.

```
[0  0  0]
[0  0  0]
```

### Diagonal Matrix
A square matrix with non-zero elements only on the diagonal.

```
[3  0  0]
[0  5  0]
[0  0  7]
```

## Matrix Operations

### Addition and Subtraction
Only matrices of the same dimensions can be added or subtracted.

```
[1  2] + [5  6] = [6   8]
[3  4]   [7  8]   [10  12]
```

### Scalar Multiplication
Multiply each element by a scalar (constant).

```
3 × [1  2] = [3   6]
    [3  4]   [9  12]
```

### Matrix Multiplication
For matrices A (m×n) and B (n×p), the product AB is (m×p).

**Rule**: Element (i,j) of AB = (row i of A) · (column j of B)

```
[1  2] × [5  6] = [1×5+2×7  1×6+2×8] = [19  22]
[3  4]   [7  8]   [3×5+4×7  3×6+4×8]   [43  50]
```

**Important**: Matrix multiplication is NOT commutative (AB ≠ BA in general).

### Transpose
Flip a matrix over its diagonal (rows become columns).

```
A = [1  2  3]     A^T = [1  4]
    [4  5  6]           [2  5]
                        [3  6]
```

### Determinant
A scalar value computed from a square matrix (denoted det(A) or |A|).

**2×2 Matrix**:
```
det([a  b]) = ad - bc
   ([c  d])
```

Example:
```
det([1  2]) = (1)(4) - (2)(3) = 4 - 6 = -2
   ([3  4])
```

**3×3 Matrix** (using cofactor expansion):
```
det([a  b  c])
   ([d  e  f]) = a(ei-fh) - b(di-fg) + c(dh-eg)
   ([g  h  i])
```

### Matrix Inverse
For square matrix A, the inverse A⁻¹ satisfies: A × A⁻¹ = A⁻¹ × A = I

**Condition**: A matrix has an inverse if and only if det(A) ≠ 0.

**2×2 Inverse Formula**:
```
[a  b]⁻¹ = 1/(ad-bc) × [ d  -b]
[c  d]                 [-c   a]
```

Example:
```
[1  2]⁻¹ = 1/-2 × [ 4  -2] = [-2   1]
[3  4]            [-3   1]   [1.5 -0.5]
```

## Systems of Linear Equations

Matrices can represent systems of equations:

```
x + 2y = 5
3x + 4y = 11
```

Can be written as:
```
[1  2] [x] = [5 ]
[3  4] [y]   [11]
```

Or: Ax = b

**Solution**: x = A⁻¹b (if A is invertible)

## Special Properties

### Symmetric Matrix
A matrix equal to its transpose: A = A^T

```
[1  2  3]
[2  4  5]
[3  5  6]
```

### Orthogonal Matrix
A matrix where A^T = A⁻¹ (columns are orthonormal vectors).

### Trace
Sum of diagonal elements: tr(A) = a₁₁ + a₂₂ + ... + aₙₙ

### Rank
The maximum number of linearly independent rows (or columns).

## Applications

### Computer Graphics
- **Transformations**: Rotation, scaling, translation
- **3D Graphics**: Perspective projection matrices

### Linear Transformations
Matrices represent linear transformations in vector spaces.

```
Rotation by θ: [cos(θ)  -sin(θ)]
               [sin(θ)   cos(θ)]
```

### Data Science and Machine Learning
- **Data Representation**: Data sets as matrices
- **Principal Component Analysis (PCA)**: Dimensionality reduction
- **Neural Networks**: Weights as matrices

### Solving Systems
- **Engineering**: Circuit analysis, structural analysis
- **Economics**: Input-output models
- **Physics**: Quantum mechanics, relativity

## Eigenvalues and Eigenvectors

For square matrix A, if Av = λv for non-zero vector v, then:
- λ is an **eigenvalue**
- v is an **eigenvector**

**Finding Eigenvalues**:
Solve det(A - λI) = 0

**Applications**:
- Stability analysis
- Google PageRank algorithm
- Quantum mechanics
- Principal Component Analysis

## Common Operations in Python (NumPy)

```python
import numpy as np

# Create matrices
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

# Addition
C = A + B

# Multiplication
D = A @ B  # or np.matmul(A, B)

# Transpose
A_T = A.T

# Determinant
det_A = np.linalg.det(A)

# Inverse
A_inv = np.linalg.inv(A)

# Eigenvalues and eigenvectors
eigenvalues, eigenvectors = np.linalg.eig(A)

# Solve Ax = b
x = np.linalg.solve(A, b)
```

## Important Theorems

### Rank-Nullity Theorem
For matrix A (m×n): rank(A) + nullity(A) = n

### Invertible Matrix Theorem
A square matrix is invertible if and only if:
- det(A) ≠ 0
- Rows are linearly independent
- Columns are linearly independent
- The equation Ax = 0 has only the trivial solution

### Properties of Determinants
- det(AB) = det(A)·det(B)
- det(A^T) = det(A)
- det(A⁻¹) = 1/det(A)

## Common Mistakes

1. Attempting to multiply incompatible matrices
2. Assuming matrix multiplication is commutative
3. Forgetting that not all matrices are invertible
4. Sign errors in determinant calculations
5. Confusing element-wise and matrix multiplication

Matrices are powerful mathematical tools that provide a compact way to represent and manipulate linear transformations, solve systems of equations, and model real-world phenomena across many disciplines.

"""
Shared pytest configuration & fixtures.
"""
import os
import sys

# Ensure project root is always on sys.path so `app.*` imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

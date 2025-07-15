#!/usr/bin/env python3
"""
Password Generation Testing for Voice Gateway.
Tests Spanish password service functionality and randomness distribution.
"""
import sys
import asyncio
from pathlib import Path
from collections import Counter
from typing import List, Tuple
import pytest

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.services.password_service import PasswordService

@pytest.mark.unit
def test_service_initialization(password_service):
    info = password_service.get_dictionary_info()
    assert info, "Dictionary info is empty"
    expected_fields = ['language', 'version', 'total_words', 'total_combinations', 'entropy_bits']
    for field in expected_fields:
        assert field in info, f"Missing field in dictionary info: {field}"

@pytest.mark.unit
def test_password_generation(password_service):
    password = password_service.generate_password()
    assert isinstance(password, str), "Password is not a string"
    assert password_service.validate_password_format(password), "Generated password failed validation"
    password_word_list = password.split()
    assert len(password_word_list) == 2, f"Password should have 2 words, got {len(password_word_list)}"
    assert password_word_list[0] != password_word_list[1], "Both words are identical"
    assert password_word_list[0] in password_service._words, "First word not in dictionary"
    assert password_word_list[1] in password_service._words, "Second word not in dictionary"

@pytest.mark.unit
def test_password_validation(password_service):
    info = password_service.get_dictionary_info()
    samples = password_service.get_sample_passwords(3)
    for password, words in samples:
        assert password_service.validate_password_format(password), f"Valid password failed: {password}"
    invalid_passwords = [
        "", "single", "one two three", "invalid notindict", "123 456", None
    ]
    for password in invalid_passwords:
        assert not password_service.validate_password_format(password), f"Invalid password passed: {password}"

@pytest.mark.unit
def test_randomness_distribution(password_service):
    sample_size = 100
    passwords = []
    all_words = []
    for _ in range(sample_size):
        password = password_service.generate_password()
        passwords.append(password)
        all_words.extend(password.split())
    unique_passwords = set(passwords)
    duplicate_rate = (sample_size - len(unique_passwords)) / sample_size * 100
    assert duplicate_rate < 10, f"Duplicate rate too high: {duplicate_rate:.1f}%"
    word_counts = Counter(all_words)
    most_common = word_counts.most_common(5)
    least_common = word_counts.most_common()[-5:]
    max_frequency = most_common[0][1] / len(all_words)
    assert max_frequency < 0.10, f"A word appears too frequently: {max_frequency:.1%}"

@pytest.mark.unit
def test_entropy_calculation(password_service):
    info = password_service.get_dictionary_info()
    assert info['entropy_bits'] > 0, "Entropy bits should be positive"

@pytest.mark.unit
def test_uniqueness_across_generations(password_service):
    iterations = 50
    passwords = set()
    for _ in range(iterations):
        password = password_service.generate_password()
        assert password not in passwords, f"Duplicate password generated: {password}"
        passwords.add(password) 
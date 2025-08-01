#!/usr/bin/env python3
"""
Spanish Dictionary Validation for Voice Gateway.
Tests dictionary structure, word criteria, and entropy calculations.
"""
import pytest
import re
from typing import Dict, Any


@pytest.mark.unit
def test_structure(test_dictionary_data):
    required_keys = ['version', 'language', 'total_words', 'words', 'entropy_bits', 'total_combinations']
    for key in required_keys:
        assert key in test_dictionary_data
    assert isinstance(test_dictionary_data['words'], list)


@pytest.mark.unit
def test_words_criteria(test_dictionary_data):
    words = test_dictionary_data['words']
    min_length = 6 
    max_length = 12 
    valid_pattern = re.compile(r'^[a-z]+$')
    
    for word in words:
        assert min_length <= len(word) <= max_length
        assert valid_pattern.match(word), f"Word '{word}' contains accents or special characters"
        assert word == word.lower(), f"Word '{word}' contains uppercase letters"


@pytest.mark.unit
def test_metadata_consistency(test_dictionary_data):
    words = test_dictionary_data['words']
    actual_count = len(words)
    declared_count = test_dictionary_data['total_words']
    assert actual_count == declared_count, f"Word count mismatch: declared {declared_count}, actual {actual_count}"
    
    unique_words = set(words)
    assert len(unique_words) == actual_count, "Found duplicate words"
    
    # Calculate combinations correctly: n * (n-1)
    expected_combinations = actual_count * (actual_count - 1)
    declared_combinations = test_dictionary_data['total_combinations']
    assert expected_combinations == declared_combinations, f"Entropy calculation error: expected {expected_combinations}, declared {declared_combinations}"


@pytest.mark.unit
def test_entropy_bits(test_dictionary_data):
    words = test_dictionary_data['words']
    combinations_without_replacement = len(words) * (len(words) - 1)
    entropy_bits = combinations_without_replacement.bit_length() - 1
    assert abs(entropy_bits - test_dictionary_data['entropy_bits']) <= 1, "Entropy bits mismatch" 
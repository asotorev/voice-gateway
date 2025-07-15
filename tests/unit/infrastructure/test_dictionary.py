#!/usr/bin/env python3
"""
Spanish Dictionary Validation for Voice Gateway.
Tests dictionary structure, word criteria, and entropy calculations.
"""
import pytest
import json
import re
from pathlib import Path
from typing import Dict, Any

@pytest.fixture(scope="module")
def dictionary_data():
    dictionary_path = Path("app/config/spanish_dictionary.json")
    assert dictionary_path.exists(), f"Dictionary file not found: {dictionary_path}"
    with open(dictionary_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.mark.unit
def test_structure(dictionary_data):
    required_keys = ['metadata', 'words']
    metadata_keys = ['version', 'language', 'total_words', 'validation_criteria', 'total_combinations', 'entropy_bits']
    for key in required_keys:
        assert key in dictionary_data
    metadata = dictionary_data['metadata']
    for key in metadata_keys:
        assert key in metadata
    assert isinstance(dictionary_data['words'], list)

@pytest.mark.unit
def test_words_criteria(dictionary_data):
    words = dictionary_data['words']
    criteria = dictionary_data['metadata']['validation_criteria']
    min_length = criteria['min_length']
    max_length = criteria['max_length']
    no_accents = criteria['no_accents']
    no_special_chars = criteria['no_special_chars']
    valid_pattern = re.compile(r'^[a-z]+$')
    for word in words:
        assert min_length <= len(word) <= max_length
        if no_accents and no_special_chars:
            assert valid_pattern.match(word), f"Word '{word}' contains accents or special characters"
        assert word == word.lower(), f"Word '{word}' contains uppercase letters"

@pytest.mark.unit
def test_metadata_consistency(dictionary_data):
    words = dictionary_data['words']
    metadata = dictionary_data['metadata']
    actual_count = len(words)
    declared_count = metadata['total_words']
    assert actual_count == declared_count, f"Word count mismatch: declared {declared_count}, actual {actual_count}"
    unique_words = set(words)
    assert len(unique_words) == actual_count, "Found duplicate words"
    expected_combinations = actual_count * (actual_count - 1)
    declared_combinations = metadata['total_combinations']
    assert expected_combinations == declared_combinations, f"Entropy calculation error: expected {expected_combinations}, declared {declared_combinations}"

@pytest.mark.unit
def test_entropy_bits(dictionary_data):
    words = dictionary_data['words']
    metadata = dictionary_data['metadata']
    combinations_without_replacement = len(words) * (len(words) - 1)
    entropy_bits = combinations_without_replacement.bit_length() - 1
    assert abs(entropy_bits - metadata['entropy_bits']) <= 1, "Entropy bits mismatch" 
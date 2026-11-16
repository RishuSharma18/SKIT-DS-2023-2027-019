
import test from 'node:test';
import assert from 'node:assert/strict';

import { findMatch } from './plateMatch.js';

// Test 1: Exact match
test('should find exact plate match', () => {
    const list = ['RJ14AB1234', 'HR26CD5678'];
    assert.equal(findMatch('RJ14AB1234', list), 'RJ14AB1234');
});

// Test 2: Lowercase input
test('should match lowercase plate', () => {
    const list = ['RJ14AB1234'];
    assert.equal(findMatch('rj14ab1234', list), 'RJ14AB1234');
});

// Test 3: Ignore spaces and hyphens
test('should ignore spaces and hyphens', () => {
    const list = ['RJ14AB1234'];
    assert.equal(findMatch('RJ 14-AB 1234', list), 'RJ14AB1234');
});

// Test 4: One character substitution
test('should match with one character substitution', () => {
    const list = ['RJ14AB1234'];
    assert.equal(findMatch('RJ14AB1235', list), 'RJ14AB1234');
});

// Test 5: One character insertion
test('should match with one extra character', () => {
    const list = ['RJ14AB1234'];
    assert.equal(findMatch('RJ14AB12345', list), 'RJ14AB1234');
});

// Test 6: One character deletion
test('should match when one character is missing', () => {
    const list = ['RJ14AB1234'];
    assert.equal(findMatch('RJ14AB123', list), 'RJ14AB1234');
});

// Test 7: More than one difference
test('should not match when more than one character differs', () => {
    const list = ['RJ14AB1234'];
    assert.equal(findMatch('RJ14XY9999', list), null);
});

// Test 8: Empty plate
test('should return null for empty plate', () => {
    assert.equal(findMatch('', ['RJ14AB1234']), null);
});

// Test 9: Empty list
test('should return null for empty list', () => {
    assert.equal(findMatch('RJ14AB1234', []), null);
});

// Test 10: Object entries
test('should support objects containing plate property', () => {
    const list = [
        { plate: 'RJ14AB1234', owner: 'User 1' },
        { plate: 'HR26CD5678', owner: 'User 2' }
    ];

    assert.deepEqual(
        findMatch('RJ14AB1234', list),
        list[0]
    );
});

// Test 11: Exact match gets priority over fuzzy match
test('should prefer exact match over fuzzy match', () => {
    const list = ['RJ14AB1235', 'RJ14AB1234'];
    assert.equal(findMatch('RJ14AB1234', list), 'RJ14AB1234');
});

// Test 12: Invalid list
test('should return null when list is not an array', () => {
    assert.equal(findMatch('RJ14AB1234', null), null);
});

// Test 13: Null entry should not crash
test('should safely handle null entries', () => {
    const list = [null, 'RJ14AB1234'];
    assert.equal(findMatch('RJ14AB1234', list), 'RJ14AB1234');
});

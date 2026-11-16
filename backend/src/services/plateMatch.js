
function normalizePlate(plate) {
    if (typeof plate !== 'string') {
        return '';
    }

    return plate.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function isOneEditAway(a, b) {
    if (Math.abs(a.length - b.length) > 1) {
        return false;
    }

    let i = 0;
    let j = 0;
    let differences = 0;

    while (i < a.length && j < b.length) {
        if (a[i] === b[j]) {
            i++;
            j++;
        } else {
            differences++;

            if (differences > 1) {
                return false;
            }

            if (a.length === b.length) {
                i++;
                j++;
            } else if (a.length > b.length) {
                i++;
            } else {
                j++;
            }
        }
    }

    if (i < a.length || j < b.length) {
        differences++;
    }

    return differences === 1;
}

export function findMatch(plate, list) {
    const target = normalizePlate(plate);

    if (!target || !Array.isArray(list)) {
        return null;
    }

    const validEntries = list.map(item => ({
        original: item,
        normalized: normalizePlate(
            typeof item === 'string' ? item : item?.plate
        )
    })).filter(entry => entry.normalized !== '');

    // First priority: exact match
    const exactMatch = validEntries.find(
        entry => entry.normalized === target
    );

    if (exactMatch) {
        return exactMatch.original;
    }

    // Second priority: one-character difference
    const fuzzyMatch = validEntries.find(
        entry => isOneEditAway(target, entry.normalized)
    );

    return fuzzyMatch ? fuzzyMatch.original : null;
}
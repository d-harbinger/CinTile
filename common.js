// CinTile — common.js
// Pure utility functions for weighted grid calculations
// No Cinnamon dependencies — safe for reuse and testing
// Algorithm: Tactile (https://gitlab.com/lundal/tactile)

/**
 * Sum all values in an array.
 */
function sumAll(array) {
    return array.reduce(function(sum, val) { return sum + val; }, 0);
}

/**
 * Sum values in array up to (but not including) index.
 */
function sumUntil(array, index) {
    return array.slice(0, index).reduce(function(sum, val) { return sum + val; }, 0);
}

/**
 * Calculate pixel geometry for a single grid cell using cumulative weights.
 *
 * @param {Object} workArea  - {x, y, width, height} of available space
 * @param {number[]} colWeights - Weight per column (length = number of columns)
 * @param {number[]} rowWeights - Weight per row (length = number of rows)
 * @param {number} col - Column index
 * @param {number} row - Row index
 * @returns {Object} {x, y, width, height} in absolute pixels
 */
function calculateCellGeometry(workArea, colWeights, rowWeights, col, row) {
    let totalColWeight = sumAll(colWeights);
    let totalRowWeight = sumAll(rowWeights);

    // Guard: if all weights are zero, return a zero-size rect at origin
    if (totalColWeight === 0 || totalRowWeight === 0) {
        return { x: workArea.x, y: workArea.y, width: 0, height: 0 };
    }

    let x = Math.floor(workArea.x + (workArea.width * sumUntil(colWeights, col)) / totalColWeight);
    let x2 = Math.floor(workArea.x + (workArea.width * sumUntil(colWeights, col + 1)) / totalColWeight);

    let y = Math.floor(workArea.y + (workArea.height * sumUntil(rowWeights, row)) / totalRowWeight);
    let y2 = Math.floor(workArea.y + (workArea.height * sumUntil(rowWeights, row + 1)) / totalRowWeight);

    return { x: x, y: y, width: x2 - x, height: y2 - y };
}

/**
 * Extract active column and row weight arrays from the settings config object.
 * Trims to the configured grid dimensions and replaces undefined values with 0.
 *
 * @param {Object} config - Settings object with gridCols, gridRows, col0Weight..col6Weight, row0Weight..row4Weight
 * @returns {Object} {colWeights: number[], rowWeights: number[]}
 */
function getActiveWeights(config) {
    let colWeights = [];
    let rowWeights = [];

    for (let i = 0; i < 7; i++) {
        colWeights.push(config['col' + i + 'Weight'] || 0);
    }

    for (let i = 0; i < 5; i++) {
        rowWeights.push(config['row' + i + 'Weight'] || 0);
    }

    colWeights = colWeights.slice(0, config.gridCols);
    rowWeights = rowWeights.slice(0, config.gridRows);

    return { colWeights: colWeights, rowWeights: rowWeights };
}
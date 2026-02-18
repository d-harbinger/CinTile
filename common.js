// common.js - Pure utility functions (no Cinnamon dependencies)

/**
 * Sum all values in an array
 */
function sumAll(array) {
    return array.reduce((sum, val) => sum + val, 0);
}

/**
 * Sum values in array up to (but not including) index
 */
function sumUntil(array, index) {
    return array.slice(0, index).reduce((sum, val) => sum + val, 0);
}

/**
 * Calculate weighted cell geometry based on Tactile's algorithm
 */
function calculateCellGeometry(workArea, colWeights, rowWeights, col, row) {
    let totalColWeight = sumAll(colWeights);
    let totalRowWeight = sumAll(rowWeights);
    
    // Calculate x position and width using weighted algorithm
    let x = Math.floor(workArea.x + (workArea.width * sumUntil(colWeights, col)) / totalColWeight);
    let x2 = Math.floor(workArea.x + (workArea.width * sumUntil(colWeights, col + 1)) / totalColWeight);
    let width = x2 - x;
    
    // Calculate y position and height using weighted algorithm
    let y = Math.floor(workArea.y + (workArea.height * sumUntil(rowWeights, row)) / totalRowWeight);
    let y2 = Math.floor(workArea.y + (workArea.height * sumUntil(rowWeights, row + 1)) / totalRowWeight);
    let height = y2 - y;
    
    return { x: x, y: y, width: width, height: height };
}

/**
 * Get active column and row weights from config
 */
function getActiveWeights(config) {
    let colWeights = [];
    let rowWeights = [];
    
    // Load column weights (max 7)
    for (let i = 0; i < 7; i++) {
        colWeights.push(config['col' + i + 'Weight'] || 0);
    }
    
    // Load row weights (max 5)
    for (let i = 0; i < 5; i++) {
        rowWeights.push(config['row' + i + 'Weight'] || 0);
    }
    
    // Trim to actual grid size
    colWeights = colWeights.slice(0, config.gridCols);
    rowWeights = rowWeights.slice(0, config.gridRows);
    
    return { colWeights: colWeights, rowWeights: rowWeights };
}
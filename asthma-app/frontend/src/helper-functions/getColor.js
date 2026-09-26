    
export function getColor(color) {
    return getComputedStyle(document.documentElement)
        .getPropertyValue(color)
        .trim()
        .replace("#", "%23");
}
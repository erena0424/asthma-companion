import { playAudio } from "./playAudio";

export function playErrorResponse(setShake) {
    navigator.vibrate?.(100);
    playAudio("buzz");
    setShake(true);
    setTimeout(() => setShake(false), 300);
}

export default playErrorResponse;
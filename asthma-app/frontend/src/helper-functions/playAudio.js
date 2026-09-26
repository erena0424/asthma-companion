let audioContext = null;

const sounds = {};

const soundFiles = {
  buzz: "error-buzz.mp3",
};

function getAudioContext() {
  if (!audioContext) {
    audioContext = new AudioContext();
  }

  return audioContext;
}

export async function preloadAudio() {
  const ctx = getAudioContext();

  if (ctx.state === "suspended") {
    await ctx.resume();
  }

  const promises = Object.entries(soundFiles).map(
    async ([name, file]) => {
      const response = await fetch(`${import.meta.env.BASE_URL}sounds/${file}`);
      const arrayBuffer = await response.arrayBuffer();

      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

      sounds[name] = audioBuffer;
    }
  );

  await Promise.all(promises);
}

export function playAudio(name) {
  const buffer = sounds[name];

  if (!buffer) {
    console.warn(`Sound "${name}" not loaded`);
    return;
  }

  const ctx = getAudioContext();

  if (ctx.state === "suspended") {
    ctx.resume();
  }

  const source = ctx.createBufferSource();

  source.buffer = buffer;
  source.connect(ctx.destination);

  source.start(0);
}
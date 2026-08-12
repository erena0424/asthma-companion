const FALLBACK_LOCATION = {
  lat: 43.0731,
  lon: -89.4012,
};

export function getUserLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({
        location: FALLBACK_LOCATION,
        permission: "unsupported",
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        resolve({
          location: {
            lat: coords.latitude,
            lon: coords.longitude,
          },
          permission: "granted",
        });
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          resolve({
            location: FALLBACK_LOCATION,
            permission: "denied",
          });
          return;
        }

        resolve({
          location: FALLBACK_LOCATION,
          permission: "unavailable",
        });
      },
      {
        enableHighAccuracy: false,
        timeout: 7000,
        maximumAge: 300000,
      }
    );
  });
}
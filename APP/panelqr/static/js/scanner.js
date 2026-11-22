(() => {
  const startButton = document.querySelector("#start-scan");
  const stopButton = document.querySelector("#stop-scan");
  const imageInput = document.querySelector("#qr-image");
  const video = document.querySelector("#qr-video");
  const status = document.querySelector("#scanner-status");
  const searchForm = document.querySelector("#panel-search");
  const searchInput = document.querySelector("#q");

  if (!startButton || !video || !status || !searchForm || !searchInput) return;

  let stream;
  let scanning = false;
  let detector;

  const report = (message) => { status.textContent = message; };

  const useResult = (value) => {
    try {
      const url = new URL(value, window.location.href);
      if (url.origin === window.location.origin) {
        const match = url.pathname.match(/^\/panel\/([^/]+)\/?$/);
        if (match) {
          window.location.assign(url.href);
          return;
        }
      }
    } catch {
      // The decoded QR value may be a panel code rather than a URL.
    }
    searchInput.value = value;
    searchForm.requestSubmit();
  };

  const stopCamera = () => {
    scanning = false;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = undefined;
    }
    video.srcObject = null;
    video.hidden = true;
    stopButton.hidden = true;
    startButton.hidden = false;
  };

  const scanFrame = async () => {
    if (!scanning) return;
    try {
      const codes = await detector.detect(video);
      if (codes.length) {
        const result = codes[0].rawValue;
        stopCamera();
        useResult(result);
        return;
      }
    } catch {
      report("No se pudo leer el código. Prueba con otra posición.");
    }
    window.requestAnimationFrame(scanFrame);
  };

  startButton.addEventListener("click", async () => {
    if (!("BarcodeDetector" in window) || !navigator.mediaDevices?.getUserMedia) {
      report("Este navegador no ofrece escaneo integrado. Busca por código o usa una imagen QR.");
      return;
    }
    try {
      detector = new window.BarcodeDetector({ formats: ["qr_code"] });
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      scanning = true;
      video.hidden = false;
      startButton.hidden = true;
      stopButton.hidden = false;
      report("Apunta la cámara al código QR.");
      window.requestAnimationFrame(scanFrame);
    } catch {
      stopCamera();
      report("No se pudo acceder a la cámara. Revisa los permisos del navegador.");
    }
  });

  stopButton.addEventListener("click", () => {
    stopCamera();
    report("Escaneo detenido.");
  });

  imageInput?.addEventListener("change", async () => {
    const file = imageInput.files?.[0];
    if (!file) return;
    if (!("BarcodeDetector" in window)) {
      report("Este navegador no puede leer imágenes QR. Busca por código.");
      return;
    }
    try {
      detector ??= new window.BarcodeDetector({ formats: ["qr_code"] });
      const codes = await detector.detect(file);
      if (!codes.length) {
        report("No se encontró un código QR en la imagen.");
        return;
      }
      useResult(codes[0].rawValue);
    } catch {
      report("No se pudo leer la imagen QR seleccionada.");
    } finally {
      imageInput.value = "";
    }
  });

  window.addEventListener("pagehide", stopCamera);
})();

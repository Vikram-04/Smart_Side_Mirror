const laneSection = document.getElementById("laneAssist");

const statusTitle = document.getElementById("statusTitle");
const statusDescription = document.getElementById("statusDescription");
const statusSymbol = document.getElementById("statusSymbol");

const distanceElement = document.getElementById("distance");
const speedElement = document.getElementById("closingSpeed");
const ttcElement = document.getElementById("ttc");
const safetyNote = document.getElementById("safetyNote");

function updateClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString(
    "en-GB",
  );
}

setInterval(updateClock, 1000);
updateClock();

async function updateDashboard() {
  try {
    const response = await fetch("/api/status", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }

    const data = await response.json();

    laneSection.classList.remove("is-unsafe", "is-empty");

    // NO VEHICLE DETECTED

    if (!data.detected) {
      laneSection.classList.add("is-empty");

      statusTitle.textContent = "NO VEHICLE DETECTED";

      statusDescription.textContent = "Mirror area is clear";

      statusSymbol.textContent = "—";

      distanceElement.innerHTML = "-- <small>cm</small>";

      speedElement.textContent = "-- cm/s";

      ttcElement.textContent = "--";

      safetyNote.textContent = "Waiting for rear vehicle detection";

      return;
    }

    // UPDATE REAL DISTANCE

    distanceElement.innerHTML = `${Number(data.distance).toFixed(1)} <small>cm</small>`;

    speedElement.textContent = `${Number(data.closing_speed).toFixed(1)} cm/s`;

    ttcElement.textContent =
      data.ttc !== null ? `${Number(data.ttc).toFixed(2)} sec` : "N/A";

    // UNSAFE

    if (data.status === "UNSAFE") {
      laneSection.classList.add("is-unsafe");

      statusTitle.textContent = "UNSAFE TO CHANGE LANE";

      statusDescription.textContent =
        "Vehicle too close or approaching rapidly";

      statusSymbol.textContent = "!";

      safetyNote.textContent = "WARNING: Do not change lane";
    }

    // SAFE
    else {
      statusTitle.textContent = "SAFE TO CHANGE LANE";

      statusDescription.textContent = "No threshold-based warning detected";

      statusSymbol.textContent = "✓";

      safetyNote.textContent = "No immediate risk detected by prototype";
    }
  } catch (error) {
    console.error("Dashboard error:", error);

    laneSection.classList.remove("is-unsafe");
    laneSection.classList.add("is-empty");

    statusTitle.textContent = "CONNECTION ERROR";

    statusDescription.textContent = "Unable to communicate with backend";

    statusSymbol.textContent = "!";

    safetyNote.textContent = "Check Python server";
  }
}

setInterval(updateDashboard, 250);

updateDashboard();

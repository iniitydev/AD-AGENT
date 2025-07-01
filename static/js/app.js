// Initialize application
document.addEventListener('DOMContentLoaded', () => {
  console.log('Sovereign platform initialized');

  // Update status indicator on header
  const statusIndicatorEl = document.getElementById('status-indicator'); // For general platform status
  if (statusIndicatorEl) {
    statusIndicatorEl.textContent = 'Sovereign Mode'; // Or dynamic status if available
  }

  // Set current year in footer
  const yearEl = document.getElementById('current-year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // Initial integrity check on load
  if (document.getElementById('integrity-status')) { // Check if the element exists on the page
    verifyIntegrity();
  }
});

// Function to verify codebase integrity via API
function verifyIntegrity() {
    console.log("Verifying integrity via API...");
    const statusEl = document.getElementById('integrity-status');
    const outputEl = document.getElementById('manifest-output');

    if (!statusEl || !outputEl) {
        console.error("Required HTML elements for integrity status/output not found.");
        return;
    }
    statusEl.textContent = "⏳ Checking...";
    statusEl.className = "label"; // Reset class

    fetch('/api/v1/integrity')
        .then(res => {
            if (!res.ok) {
                // Try to get error detail from response if possible
                return res.json().then(errData => {
                    throw new Error(`HTTP error ${res.status}: ${errData.detail || res.statusText}`);
                }).catch(() => { // Fallback if res.json() fails or no detail
                    throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
                });
            }
            return res.json();
        })
        .then(data => { // 'data' is the result from verify_integrity script (via API)
            outputEl.textContent = JSON.stringify(data, null, 2); // Display full details
            if (data.verified) {
                statusEl.textContent = "✅ Verified";
                statusEl.className = "label label-success";
            } else if (data.error_message) { // Script itself had an error (e.g. manifest not found)
                statusEl.textContent = `❌ Error: ${data.error_message.substring(0,100)}`; // Show snippet of error
                statusEl.className = "label label-danger";
            } else if (data.failed_files_details && data.failed_files_details.length > 0) {
                 statusEl.textContent = "⚠️ Tampered";
                 statusEl.className = "label label-danger";
            } else if (data.signature_verified === false) {
                statusEl.textContent = "⚠️ Invalid Signature";
                statusEl.className = "label label-danger";
            }
             else { // Other non-verified cases
                statusEl.textContent = "⚠️ Not Verified";
                statusEl.className = "label label-danger";
            }
        })
        .catch(error => {
            console.error("Error during integrity check:", error);
            statusEl.textContent = "❌ Error Checking";
            statusEl.className = "label label-danger";
            outputEl.textContent = `Error: ${error.message}`;
        });
}

// Function to generate a new manifest via API
function generateManifest() {
    console.log("Generating new manifest via API...");
    const statusEl = document.getElementById('integrity-status');
    const outputEl = document.getElementById('manifest-output');

    if (!statusEl || !outputEl) {
        console.error("Required HTML elements for integrity status/output not found.");
        return;
    }
    statusEl.textContent = "⏳ Generating...";
    statusEl.className = "label";
    outputEl.textContent = "Generating new manifest...";

    fetch('/api/v1/integrity/generate', { method: 'POST' })
        .then(res => {
            if (!res.ok) {
                return res.json().then(errData => {
                    throw new Error(`HTTP error ${res.status}: ${errData.detail || res.statusText}`);
                }).catch(() => {
                    throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.status === "success" && data.manifest) {
                outputEl.textContent = JSON.stringify(data.manifest, null, 2);
                // Call verifyIntegrity() to update the status based on the new manifest
                // This creates a chain, ensure verifyIntegrity() updates status correctly
                verifyIntegrity();
            } else {
                outputEl.textContent = `Manifest Generation Failed:\n${JSON.stringify(data, null, 2)}`;
                statusEl.textContent = "❌ Error Generating";
                statusEl.className = "label label-danger";
            }
        })
        .catch(error => {
            console.error("Error generating manifest:", error);
            outputEl.textContent = `Error generating manifest: ${error.message}`;
            statusEl.textContent = "❌ Error Generating";
            statusEl.className = "label label-danger";
        });
}

// Placeholder for verifyDataIntegrity - to be implemented in B3
function verifyDataIntegrity() {
    console.log("Verifying data integrity (placeholder)...");
    const dataStatusEl = document.getElementById('data-status');
    if (dataStatusEl) {
        dataStatusEl.innerHTML = `<span class="label">⏳ Checking data...</span>`;
        // Replace with actual API call in B3
        setTimeout(() => { // Simulate API call
             dataStatusEl.innerHTML = `<span class="label label-default">Data check N/A</span>`;
        }, 1000);
    } else {
        console.error("Element with ID 'data-status' not found.");
    }
}

// Placeholder for other JS functions from user's future plans (e.g., ledger, export)
// async function connectLedger() { ... }
// async function storeManifestOnLedger() { ... }
// function exportManifest(format) { ... }
// function verifyExport() { ... }
// async function loadIdentity() { ... }
// async function generateIdentity() { ... }
// async function registerDID() { ... }
// async function initLedger() { ... }
// async function verifyOnLedger() { ... }

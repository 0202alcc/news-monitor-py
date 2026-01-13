// main.js

// Initialize GPT globally
window.googletag = window.googletag || { cmd: [] };

// Initialize Prebid globally
window.pbjs = window.pbjs || {};
pbjs.que = pbjs.que || [];

/**
 * Initialize GPT slot for a given div ID
 */
function defineGptSlot(adUnitPath, divId, size) {
    let slot;
    googletag.cmd.push(function() {
        slot = googletag.defineSlot(adUnitPath, size, divId)
            .addService(googletag.pubads());
        googletag.pubads().enableSingleRequest();
        googletag.enableServices();
        googletag.display(divId);
    });
    return slot;
}

/**
 * Initialize Prebid ad for a specific div
 */
function initPrebidAd(adUnitCode, adSizes, bidders = []) {
    pbjs.que.push(function() {
        pbjs.addAdUnits([{
            code: adUnitCode,
            mediaTypes: { banner: { sizes: adSizes } },
            bids: bidders
        }]);
        pbjs.requestBids({
            bidsBackHandler: function() {
                if (googletag.pubads) {
                    googletag.cmd.push(function() {
                        pbjs.setTargetingForGPTAsync();
                        if (window[adUnitCode]) {
                            googletag.pubads().refresh([window[adUnitCode]]);
                        }
                    });
                }
            }
        });
    });
}

/**
 * Initialize all ads in a container (used for tab content)
 */
function initAdsInContainer(container) {
    const adDivs = container.querySelectorAll('.ad-slot');
    adDivs.forEach(div => {
        const width = parseInt(div.style.width) || 300;
        const height = parseInt(div.style.height) || 250;
        const size = [width, height];

        // Only define GPT slot if not already defined
        if (!window[div.id]) {
            window[div.id] = defineGptSlot('/1234567/news-dashboard', div.id, size);
        }

        // Initialize Prebid for this ad
        initPrebidAd(div.id, [size], [
            // Example bidder configuration
            // { bidder: 'appnexus', params: { placementId: '12345678' } }
        ]);
    });
}

/**
 * Tab switching logic
 */
function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    const tab = document.getElementById('tab-' + tabId);
    const content = document.getElementById('content-' + tabId);
    if (tab && content) {
        tab.classList.add('active');
        content.classList.add('active');

        // Initialize any ads inside this tab
        initAdsInContainer(content);
    }
}

// Activate first tab on page load and initialize ads
window.addEventListener('DOMContentLoaded', () => {
    const firstTab = document.querySelector('.tab');
    if (firstTab) firstTab.click();

    // Initialize global ads (outside tabs)
    const globalAdDivs = document.querySelectorAll('#ad-slot-global');
    globalAdDivs.forEach(div => initAdsInContainer(div));
});

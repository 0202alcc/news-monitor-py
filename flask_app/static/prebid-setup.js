// prebid-setup.js
window.pbjs = window.pbjs || {};
pbjs.que = pbjs.que || [];

/**
 * Initialize all ad slots on the page dynamically.
 * Finds any element with class "ad-slot" and creates a Prebid unit.
 */
function initAllAds() {
    const adDivs = document.querySelectorAll('.ad-slot');
    if (!adDivs.length) return;

    const adUnits = Array.from(adDivs).map(div => {
        const width = parseInt(div.style.width) || 300;
        const height = parseInt(div.style.height) || 250;

        return {
            code: div.id,
            mediaTypes: { banner: { sizes: [[width, height]] } },
            bids: [] // You can add default bidders here
        };
    });

    pbjs.que.push(function() {
        pbjs.addAdUnits(adUnits);
        pbjs.requestBids({
            bidsBackHandler: function() {
                if (typeof googletag !== 'undefined' && googletag.pubads) {
                    googletag.cmd.push(function() {
                        pbjs.setTargetingForGPTAsync();
                        // Refresh all ad slots
                        adDivs.forEach(div => {
                            if (window[div.id]) googletag.pubads().refresh([window[div.id]]);
                        });
                    });
                }
            }
        });
    });
}

/**
 * Initialize ads inside a specific container (useful for tab switching)
 */
function initAdsInContainer(container) {
    const adDivs = container.querySelectorAll('.ad-slot');
    if (!adDivs.length) return;

    const adUnits = Array.from(adDivs).map(div => {
        const width = parseInt(div.style.width) || 300;
        const height = parseInt(div.style.height) || 250;

        return {
            code: div.id,
            mediaTypes: { banner: { sizes: [[width, height]] } },
            bids: []
        };
    });

    pbjs.que.push(function() {
        pbjs.addAdUnits(adUnits);
        pbjs.requestBids({
            bidsBackHandler: function() {
                if (typeof googletag !== 'undefined' && googletag.pubads) {
                    googletag.cmd.push(function() {
                        pbjs.setTargetingForGPTAsync();
                        adDivs.forEach(div => {
                            if (window[div.id]) googletag.pubads().refresh([window[div.id]]);
                        });
                    });
                }
            }
        });
    });
}

// Initialize all ads on page load
window.addEventListener('DOMContentLoaded', initAllAds);

/**
 * Perspective Component Discovery Script
 *
 * Discovers and extracts metadata from interactive components on a Perspective page.
 * Handles Shadow DOM and custom Perspective components.
 *
 * Usage:
 *   const result = discoverPerspectiveComponents('body', {
 *     types: ['button', 'input', 'link', 'dropdown', 'toggle'],
 *     excludeSelectors: ['.ignition-system-element']
 *   });
 */

(function() {
    'use strict';

    /**
     * Check if an element is interactive
     */
    function isInteractive(element) {
        const tagName = element.tagName.toLowerCase();
        const role = element.getAttribute('role');

        // Standard HTML interactive elements
        const interactiveTags = [
            'button', 'a', 'input', 'select', 'textarea',
            'details', 'summary'
        ];

        // ARIA roles that indicate interactivity
        const interactiveRoles = [
            'button', 'link', 'menuitem', 'tab', 'checkbox',
            'radio', 'switch', 'slider', 'spinbutton', 'textbox'
        ];

        // Check tag name
        if (interactiveTags.includes(tagName)) {
            return true;
        }

        // Check ARIA role
        if (role && interactiveRoles.includes(role)) {
            return true;
        }

        // Check for click handlers (custom components)
        if (element.onclick || element.getAttribute('onclick')) {
            return true;
        }

        // Check for Perspective-specific attributes
        if (element.hasAttribute('data-component-path') ||
            element.hasAttribute('data-component-id') ||
            element.classList.contains('ia_button') ||
            element.classList.contains('ia_dropdown') ||
            element.classList.contains('ia_toggle')) {
            return true;
        }

        return false;
    }

    /**
     * Determine component type from element
     */
    function getComponentType(element) {
        const tagName = element.tagName.toLowerCase();
        const role = element.getAttribute('role');

        // Check Perspective-specific classes
        if (element.classList.contains('ia_button')) return 'button';
        if (element.classList.contains('ia_dropdown')) return 'dropdown';
        if (element.classList.contains('ia_toggle')) return 'toggle';
        if (element.classList.contains('ia_input')) return 'input';

        // Check ARIA role
        if (role) return role;

        // Check tag name
        if (tagName === 'button') return 'button';
        if (tagName === 'a') return 'link';
        if (tagName === 'input') return element.type || 'input';
        if (tagName === 'select') return 'dropdown';
        if (tagName === 'textarea') return 'textarea';

        return 'unknown';
    }

    /**
     * Extract metadata from element
     */
    function extractMetadata(element, index) {
        const rect = element.getBoundingClientRect();

        return {
            id: element.id || `component-${index}`,
            index: index,
            type: getComponentType(element),
            tagName: element.tagName.toLowerCase(),
            className: element.className || '',

            // Selectors (prioritized)
            selector: getOptimalSelector(element),
            cssPath: getCSSPath(element),
            xpath: getXPath(element),

            // Text content
            text: getElementText(element),
            label: getElementLabel(element),
            placeholder: element.getAttribute('placeholder') || '',
            title: element.getAttribute('title') || '',
            ariaLabel: element.getAttribute('aria-label') || '',

            // Position and visibility
            position: {
                x: Math.round(rect.left),
                y: Math.round(rect.top),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            },
            visible: isElementVisible(element),

            // State
            disabled: element.disabled || element.getAttribute('aria-disabled') === 'true',
            readonly: element.readOnly || element.getAttribute('aria-readonly') === 'true',

            // Perspective-specific attributes
            componentPath: element.getAttribute('data-component-path') || '',
            componentId: element.getAttribute('data-component-id') || '',

            // Custom data attributes
            dataAttributes: getDataAttributes(element)
        };
    }

    /**
     * Get optimal selector for element (most reliable first)
     */
    function getOptimalSelector(element) {
        // 1. ID (most reliable)
        if (element.id) {
            return `#${element.id}`;
        }

        // 2. Perspective-specific data attributes
        if (element.getAttribute('data-component-path')) {
            return `[data-component-path="${element.getAttribute('data-component-path')}"]`;
        }

        if (element.getAttribute('data-component-id')) {
            return `[data-component-id="${element.getAttribute('data-component-id')}"]`;
        }

        // 3. Name attribute (for inputs)
        if (element.name) {
            return `[name="${element.name}"]`;
        }

        // 4. CSS path (fallback)
        return getCSSPath(element);
    }

    /**
     * Get CSS path to element
     */
    function getCSSPath(element) {
        const path = [];
        let current = element;

        while (current && current !== document.body) {
            let selector = current.tagName.toLowerCase();

            if (current.id) {
                selector += `#${current.id}`;
                path.unshift(selector);
                break;
            } else if (current.className) {
                const classes = Array.from(current.classList)
                    .filter(c => c && !c.startsWith('_'))  // Filter out generated classes
                    .join('.');
                if (classes) {
                    selector += `.${classes}`;
                }
            }

            path.unshift(selector);
            current = current.parentElement;
        }

        return path.join(' > ');
    }

    /**
     * Get XPath to element
     */
    function getXPath(element) {
        if (element.id) {
            return `//*[@id="${element.id}"]`;
        }

        const path = [];
        let current = element;

        while (current && current !== document.body) {
            let index = 1;
            let sibling = current.previousElementSibling;

            while (sibling) {
                if (sibling.tagName === current.tagName) {
                    index++;
                }
                sibling = sibling.previousElementSibling;
            }

            const tagName = current.tagName.toLowerCase();
            path.unshift(`${tagName}[${index}]`);
            current = current.parentElement;
        }

        return `/${path.join('/')}`;
    }

    /**
     * Get visible text from element
     */
    function getElementText(element) {
        // Try innerText first (visible text only)
        if (element.innerText) {
            return element.innerText.trim().substring(0, 200);  // Limit length
        }

        // Fallback to textContent
        return (element.textContent || '').trim().substring(0, 200);
    }

    /**
     * Get label for element (for inputs)
     */
    function getElementLabel(element) {
        // Check aria-labelledby
        const labelledBy = element.getAttribute('aria-labelledby');
        if (labelledBy) {
            const labelElement = document.getElementById(labelledBy);
            if (labelElement) {
                return labelElement.textContent.trim();
            }
        }

        // Check associated label (for inputs)
        if (element.id) {
            const label = document.querySelector(`label[for="${element.id}"]`);
            if (label) {
                return label.textContent.trim();
            }
        }

        // Check parent label
        const parentLabel = element.closest('label');
        if (parentLabel) {
            return parentLabel.textContent.trim();
        }

        return '';
    }

    /**
     * Check if element is visible
     */
    function isElementVisible(element) {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            style.opacity !== '0' &&
            rect.width > 0 &&
            rect.height > 0
        );
    }

    /**
     * Get all data-* attributes
     */
    function getDataAttributes(element) {
        const data = {};

        for (const attr of element.attributes) {
            if (attr.name.startsWith('data-')) {
                const key = attr.name.substring(5);  // Remove 'data-' prefix
                data[key] = attr.value;
            }
        }

        return data;
    }

    /**
     * Traverse DOM tree including Shadow DOM
     */
    function traverse(element, components, options, parentPath = '') {
        // Check if element should be excluded
        if (options.excludeSelectors) {
            for (const excludeSelector of options.excludeSelectors) {
                if (element.matches && element.matches(excludeSelector)) {
                    return;
                }
            }
        }

        // Check if element is interactive
        if (isInteractive(element)) {
            const componentType = getComponentType(element);

            // Check if type is allowed
            if (!options.types || options.types.length === 0 || options.types.includes(componentType)) {
                const metadata = extractMetadata(element, components.length);
                components.push(metadata);
            }
        }

        // Traverse children
        for (const child of element.children) {
            traverse(child, components, options, parentPath);
        }

        // Traverse Shadow DOM if present
        if (element.shadowRoot) {
            for (const shadowChild of element.shadowRoot.children) {
                traverse(shadowChild, components, options, parentPath + '/shadow');
            }
        }
    }

    /**
     * Main discovery function
     *
     * @param {string} rootSelector - Root element selector to start discovery
     * @param {Object} options - Discovery options
     * @param {Array<string>} options.types - Component types to include (empty = all)
     * @param {Array<string>} options.excludeSelectors - CSS selectors to exclude
     * @returns {Object} Discovery result
     */
    window.discoverPerspectiveComponents = function(rootSelector, options = {}) {
        const root = document.querySelector(rootSelector);

        if (!root) {
            return {
                success: false,
                error: `Root element not found: ${rootSelector}`,
                components: []
            };
        }

        const components = [];

        try {
            traverse(root, components, options);

            return {
                success: true,
                count: components.length,
                components: components,
                timestamp: new Date().toISOString(),
                rootSelector: rootSelector
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                components: components,  // Return partial results
                timestamp: new Date().toISOString(),
                rootSelector: rootSelector
            };
        }
    };

    // Return true to indicate script loaded successfully
    return true;
})();

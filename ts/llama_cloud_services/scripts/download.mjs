import fs from 'fs';

async function downloadOpenApiSpec() {
    try {
        const response = await fetch('https://api.cloud.llamaindex.ai/api/openapi.json');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        fs.writeFileSync('openapi.json', JSON.stringify(data, null, 2));
        console.log('Successfully downloaded openapi.json');
    } catch (error) {
        console.error('Error downloading OpenAPI spec:', error);
        process.exit(1);
    }
}

downloadOpenApiSpec();

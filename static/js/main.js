document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    const downloadBtn = document.getElementById('download-btn');
    const templateType = document.getElementById('template-type');
    const requirements = document.getElementById('requirements');
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('result-container');
    const result = document.getElementById('result');
    
    generateBtn.addEventListener('click', async function() {
        if (!requirements.value.trim()) {
            alert('Please enter document requirements');
            return;
        }
        
        loading.style.display = 'block';
        resultContainer.style.display = 'none';
        
        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    template_type: templateType.value,
                    requirements: requirements.value
                })
            });

            const data = await response.json();
            loading.style.display = 'none';

            if (data.success) {
                // Use the formatted HTML from the backend
                result.innerHTML = data.formatted_html;
                resultContainer.style.display = 'block';
                resultContainer.scrollIntoView({ behavior: 'smooth' });
            } else {
                alert('Error: ' + (data.error || 'Failed to generate document'));
            }
        } catch (error) {
            loading.style.display = 'none';
            console.error('Error:', error);
            alert('An error occurred while generating the document');
        }
    });

    // Download as PDF
    downloadBtn.addEventListener('click', async function() {
        try {
            // Load logo image first
            const logoImg = document.querySelector('#piramal-logo-pdf');
            await new Promise((resolve, reject) => {
                if (logoImg.complete) resolve();
                logoImg.onload = resolve;
                logoImg.onerror = reject;
            });

            const { jsPDF } = window.jspdf;
            const doc = new jsPDF({
                orientation: 'portrait',
                unit: 'mm',
                format: 'a4'
            });

            // Capture header with logo
            const header = document.getElementById('pdf-header');
            header.style.display = 'block';
            const headerCanvas = await html2canvas(header, {
                scale: 2,
                useCORS: true,
                allowTaint: true,
                logging: false
            });
            header.style.display = 'none';

            // Capture main content
            const contentCanvas = await html2canvas(result, {
                scale: 2,
                useCORS: true,
                allowTaint: true,
                logging: false
            });

            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 10;

            // Calculate dimensions
            const headerHeight = 30;
            const contentWidth = pageWidth - (margin * 2);
            const contentHeight = (contentCanvas.height * contentWidth) / contentCanvas.width;

            let heightLeft = contentHeight;
            let position = headerHeight + margin;
            let pageNumber = 1;

            function addHeaderToPage() {
                const headerWidth = pageWidth - (margin * 2);
                const headerImgHeight = (headerCanvas.height * headerWidth) / headerCanvas.width;
                doc.addImage(headerCanvas.toDataURL('image/png', 1.0), 'PNG', margin, margin, headerWidth, headerImgHeight);
            }

            // First page
            addHeaderToPage();
            doc.addImage(contentCanvas.toDataURL('image/png', 1.0), 'PNG', margin, position, contentWidth, contentHeight);
            heightLeft -= (pageHeight - position);

            // Additional pages
            while (heightLeft >= 0) {
                doc.addPage();
                addHeaderToPage();
                position = heightLeft - contentHeight + headerHeight + margin;
                doc.addImage(contentCanvas.toDataURL('image/png', 1.0), 'PNG', margin, headerHeight + margin, contentWidth, contentHeight);
                heightLeft -= (pageHeight - (headerHeight + margin));
            }

            // Save PDF
            const docType = templateType.value.toUpperCase();
            const filename = `Piramal_${docType}_${new Date().toISOString().slice(0,10)}.pdf`;
            doc.save(filename);

        } catch (error) {
            console.error('Error generating PDF:', error);
            alert('Error generating PDF. Please try again.');
        }
    });
});
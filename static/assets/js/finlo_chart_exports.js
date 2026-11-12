// Loaded only after an explicit PNG/PDF export request.
Object.assign(EChartsConfig, {
    exportChart: function(chartInstance, filename = 'chart', format = 'png') {
        if (!chartInstance) return;

        const url = chartInstance.getDataURL({
            pixelRatio: 2,
            backgroundColor: '#fff',
            excludeComponents: ['toolbox']
        });

        const link = document.createElement('a');
        link.download = `${filename}.${format}`;
        link.href = url;
        link.click();
    },


    getChartInstanceByDomId: function(chartDomId) {
        if (!chartDomId) return null;
        var dom = document.getElementById(chartDomId);
        if (dom && typeof echarts !== 'undefined' && echarts.getInstanceByDom) {
            var inst = echarts.getInstanceByDom(dom);
            if (inst && !inst.isDisposed()) return inst;
        }
        if (window.chartInstances) {
            var key = 'finlo-chart-view-' + chartDomId;
            if (window.chartInstances[key] && window.chartInstances[key].instance) {
                var i = window.chartInstances[key].instance;
                if (i && !i.isDisposed()) return i;
            }
        }
        if (chartDomId.indexOf('chart-') === 0) {
            var pk = chartDomId.split('-')[1];
            if (pk && window['reportChartInstance_' + pk]) {
                var r = window['reportChartInstance_' + pk];
                if (r && !r.isDisposed()) return r;
            }
        }
        return null;
    },

    ensureJsPDFLoaded: function(onSuccess, onError) {
        if (window.jspdf && window.jspdf.jsPDF) {
            if (onSuccess) onSuccess();
            return;
        }
        var scriptSrc = window.finloJsPDFScriptUrl || '/static/assets/js/jspdf/jspdf.umd.min.js';
        var existing = document.querySelector('script[src="' + scriptSrc + '"]');
        if (existing) {
            if (existing.dataset.loaded === 'true') {
                if (window.jspdf && window.jspdf.jsPDF) {
                    if (onSuccess) onSuccess();
                } else if (onError) {
                    onError(new Error('jsPDF failed to initialize'));
                }
            } else {
                existing.addEventListener('load', function() {
                    if (window.jspdf && window.jspdf.jsPDF) {
                        if (onSuccess) onSuccess();
                    } else if (onError) {
                        onError(new Error('jsPDF failed to initialize'));
                    }
                }, { once: true });
                existing.addEventListener('error', function(err) {
                    if (onError) onError(err);
                }, { once: true });
            }
            return;
        }
        var script = document.createElement('script');
        script.src = scriptSrc;
        script.async = true;
        script.onload = function() {
            script.dataset.loaded = 'true';
            if (window.jspdf && window.jspdf.jsPDF) {
                if (onSuccess) onSuccess();
            } else if (onError) {
                onError(new Error('jsPDF failed to initialize'));
            }
        };
        script.onerror = function(err) {
            script.remove();
            if (onError) onError(err || new Error('Failed to load jsPDF'));
        };
        document.head.appendChild(script);
    },

    exportChartAsPDF: function(chartDomId, filename) {
        var self = this;
        var doExport = function() {
            try {
                if (!window.jspdf || !window.jspdf.jsPDF) {
                    console.error('jsPDF library is not loaded.');
                    if (typeof alert !== 'undefined') {
                        alert('Failed to export PDF: jsPDF library is not loaded.');
                    }
                    return;
                }
                var chartInstance = self.getChartInstanceByDomId(chartDomId);
                if (!chartInstance) {
                    console.error('Chart instance not found for id:', chartDomId);
                    if (typeof alert !== 'undefined') {
                        alert('Failed to export PDF: Chart instance not available.');
                    }
                    return;
                }
                chartInstance.resize();
                var imgData = chartInstance.getDataURL({
                    pixelRatio: 2,
                    backgroundColor: '#fff',
                    excludeComponents: ['toolbox']
                });
                if (!imgData) {
                    console.error('Failed to generate chart image data.');
                    if (typeof alert !== 'undefined') {
                        alert('Failed to export PDF: Could not generate chart image.');
                    }
                    return;
                }
                var jsPDF = window.jspdf.jsPDF;
                var pdf = new jsPDF({
                    orientation: 'landscape',
                    unit: 'px',
                    format: [800, 400]
                });
                var imgProps = pdf.getImageProperties(imgData);
                var pdfWidth = pdf.internal.pageSize.getWidth();
                var pdfHeight = pdf.internal.pageSize.getHeight();
                var imgWidth = 700;
                var imgHeight = (imgProps.height * imgWidth) / imgProps.width;
                var x = (pdfWidth - imgWidth) / 2;
                var y = (pdfHeight - imgHeight) / 2;
                pdf.addImage(imgData, 'PNG', x, y, imgWidth, imgHeight);
                pdf.save((filename || 'chart') + '.pdf');
            } catch (error) {
                console.error('Error exporting chart as PDF:', error);
                if (typeof alert !== 'undefined') {
                    alert('Failed to export PDF: An error occurred.');
                }
            }
        };

        if (window.jspdf && window.jspdf.jsPDF) {
            doExport();
        } else {
            self.ensureJsPDFLoaded(doExport, function(err) {
                console.error('Error loading jsPDF on demand:', err);
                if (typeof alert !== 'undefined') {
                    alert('Failed to export PDF: Could not load PDF export library.');
                }
            });
        }
    }
});

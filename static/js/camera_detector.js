/**
 * Camera Detector - Building Identification
 * Handles image upload and ML-based building detection
 */

class CameraDetector {
    constructor() {
        this.modal = document.getElementById('cameraModal');
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('buildingImage');
        this.previewArea = document.getElementById('previewArea');
        this.previewImage = document.getElementById('previewImage');
        this.loadingArea = document.getElementById('cameraLoading');
        this.resultArea = document.getElementById('cameraResult');
        
        this.selectedFile = null;
        
        this.init();
    }
    
    init() {
        console.log('📸 Camera Detector initialized');
        
        // Open camera modal
        document.getElementById('cameraBtn').addEventListener('click', () => {
            this.openModal();
        });
        
        // Close modal
        document.getElementById('closeCameraModal').addEventListener('click', () => {
            this.closeModal();
        });
        
        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e);
        });
        
        // Identify button
        document.getElementById('identifyBtn').addEventListener('click', () => {
            this.identifyBuilding();
        });
        
        // Result OK button
        document.getElementById('resultOkBtn').addEventListener('click', () => {
            const name = this.lastDetectedName;
            const id = this.lastDetectedBuilding;
            this.closeModal();
            if (id && window.mobileApp) {
                // Open chat panel if it's minimized
                const chatbotContainer = document.getElementById('chatbotContainer');
                const chatToggle = document.getElementById('chatToggle');
                if (chatbotContainer && chatbotContainer.classList.contains('minimized')) {
                    if (chatToggle) chatToggle.click();
                }
                setTimeout(() => {
                    window.mobileApp.addMessage('bot',
                    'I identified that as <strong>' + name + '</strong>. Would you like me to navigate you there? <br><br><button onclick="window.showNavigation(\'Gate 1\',\'' + id + '\');this.parentElement.parentElement.innerHTML=\'✅ Navigating to ' + name + '...\';" style="background:#006341;color:white;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:13px;margin-top:4px;">Yes, take me there!</button>');
                }, 300);
            }
        });
        
        // Close modal on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    }
    
    openModal() {
        this.modal.classList.add('active');
        this.resetModal();
    }
    
    closeModal() {
        this.modal.classList.remove('active');
        this.resetModal();
    }
    
    resetModal() {
        this.uploadArea.style.display = 'block';
        this.previewArea.style.display = 'none';
        this.loadingArea.style.display = 'none';
        this.resultArea.style.display = 'none';
        this.fileInput.value = '';
        this.selectedFile = null;
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file!');
            return;
        }
        
        this.selectedFile = file;
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            this.previewImage.src = e.target.result;
            this.uploadArea.style.display = 'none';
            this.previewArea.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
    
    async identifyBuilding() {
        if (!this.selectedFile) return;
        
        // Show loading
        this.previewArea.style.display = 'none';
        this.loadingArea.style.display = 'block';
        
        try {
            // Create form data
            const formData = new FormData();
            formData.append('image', this.selectedFile);
            
            // Send to ML detection endpoint
            const response = await fetch('/detect-building', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success && data.detections && data.detections.length > 0) {
                // Building detected!
                const detection = data.detections[0];
                this.showResult(detection);
            } else {
                // No building detected
                this.showError('No building detected. Please try a clearer photo.');
            }
            
        } catch (error) {
            console.error('Detection error:', error);
            this.showError('Failed to identify building. Please try again.');
        }
    }
    
    showResult(detection) {
        const buildingName = detection.class_name;
        const confidence = detection.confidence;
        
        // Map model class names to DB building IDs
        const classToId = {
            'AYUNTAMIENTO': 'Admin',
            'FOODSQUARE': 'Square',
            'LIBRARY': 'Library',
            'JFH': 'JFH',
            'CEAT': 'CEAT',
            'CBAA': 'CBAA',
            'CTH': 'CTH',
            'CTHM': 'CTHM',
            'CHAPEL': 'Chapel',
            'bad': null
        };
        
        // Get building info
        const dbId = classToId[buildingName] !== undefined ? classToId[buildingName] : buildingName;
        const buildingInfo = this.getBuildingInfo(dbId || buildingName);
        this.lastDetectedBuilding = dbId;
        this.lastDetectedName = buildingInfo.name;
        
        // Update UI
        document.getElementById('buildingName').textContent = buildingInfo.name;
        document.getElementById('confidence').textContent = `Confidence: ${(confidence * 100).toFixed(1)}%`;
        document.getElementById('buildingDescription').textContent = buildingInfo.description;
        
        // Show result
        this.loadingArea.style.display = 'none';
        this.resultArea.style.display = 'block';
        
        console.log(`✅ Identified: ${buildingName} (${(confidence * 100).toFixed(1)}%)`);
    }
    
    showError(message) {
        this.loadingArea.style.display = 'none';
        this.uploadArea.style.display = 'block';
        alert(message);
    }
    
    getBuildingInfo(buildingId) {
        // Building information database
        const buildings = {
            'CEAT': {
                name: 'CEAT',
                fullName: 'College of Engineering, Architecture and Technology',
                description: 'The College of Engineering, Architecture and Technology building houses the Engineering, Architecture, and Technology programs.'
            },
            'Library': {
                name: 'Rizal Library',
                fullName: 'Rizal Library',
                description: 'The main campus library providing academic resources and study spaces for students.'
            },
            'CBAA': {
                name: 'CBAA',
                fullName: 'College of Business Administration and Accountancy',
                description: 'Houses the Business Administration and Accountancy programs.'
            },
            'JFH': {
                name: 'JFH',
                fullName: 'Jose Fernandez Hall',
                description: 'Multi-purpose building for various college programs and facilities.'
            },
            'Admin': {
                name: 'Ayuntamiento',
                fullName: 'Ayuntamiento de Gonzalez (Administration Building)',
                description: 'Main administration building housing the university offices.'
            },
            'CTHM': {
                name: 'CTHM',
                fullName: 'College of Tourism and Hospitality Management',
                description: 'Houses the Tourism and Hospitality Management programs.'
            },
            'CTH': {
                name: 'CTH',
                fullName: 'Candido Tirona Hall',
                description: 'Building for various academic programs.'
            },
            'Gate 1': {
                name: 'Gate 1',
                fullName: 'Main Entrance (Gate 1)',
                description: 'Main entrance to DLSU-Dasmariñas campus.'
            },
            'Gate 2': {
                name: 'Gate 2',
                fullName: 'Gate 2 Entrance',
                description: 'Secondary entrance to the campus.'
            },
            'Gate 3': {
                name: 'Gate 3',
                fullName: 'Gate 3 Entrance',
                description: 'North entrance to the campus.'
            },
            'Gate 4': {
                name: 'Gate 4',
                fullName: 'Gate 4 (FDH Gate)',
                description: 'Entrance near the FDH building.'
            }
        };
        
        return buildings[buildingId] || {
            name: buildingId,
            fullName: buildingId,
            description: 'DLSU-Dasmariñas campus building.'
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.cameraDetector = new CameraDetector();
});

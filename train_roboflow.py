"""
Building Recognition Training with PyTorch (GPU Support)
Custom dataset loader that only uses folders with actual images
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, models
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import random

class BuildingDataset(Dataset):
    """Custom dataset that only includes folders with images"""
    
    def __init__(self, root_dir, class_names, transform=None):
        """
        Args:
            root_dir: Path to train/valid/test directory
            class_names: List of class names to include
            transform: Optional transform to apply
        """
        self.root_dir = Path(root_dir)
        self.class_names = class_names
        self.transform = transform
        self.samples = []
        self.class_to_idx = {name: idx for idx, name in enumerate(class_names)}
        
        # Build samples list
        for class_name in class_names:
            class_dir = self.root_dir / class_name
            if class_dir.exists():
                # Find all image files
                image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
                images = []
                for ext in image_extensions:
                    images.extend(class_dir.glob(ext))
                
                for img_path in images:
                    self.samples.append((str(img_path), self.class_to_idx[class_name]))
        
        print(f"  Loaded {len(self.samples)} images from {root_dir}")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        return image, label

class BuildingTrainer:
    """PyTorch trainer for building recognition with GPU support"""
    
    def __init__(self, dataset_dir='dataset', img_size=224, batch_size=32):
        self.dataset_dir = Path(dataset_dir)
        self.img_size = img_size
        self.batch_size = batch_size
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.class_names = []
        self.history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}
        
    def check_gpu(self):
        """Check GPU availability"""
        if torch.cuda.is_available():
            print(f"✅ GPU available: {torch.cuda.get_device_name(0)}")
            print(f"   CUDA Version: {torch.version.cuda}")
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            # Set for better performance
            torch.backends.cudnn.benchmark = True
            return True
        else:
            print("ℹ️  No GPU found - using CPU")
            return False
    
    def get_non_empty_classes(self):
        """Get only classes that have actual images"""
        
        train_dir = self.dataset_dir / 'train'
        
        non_empty_classes = []
        
        if train_dir.exists():
            for class_dir in train_dir.iterdir():
                if class_dir.is_dir():
                    # Count images in train folder
                    img_count = len(list(class_dir.glob('*.jpg')) + 
                                  list(class_dir.glob('*.jpeg')) + 
                                  list(class_dir.glob('*.png')))
                    
                    if img_count > 0:
                        non_empty_classes.append(class_dir.name)
                        print(f"  ✅ {class_dir.name}: {img_count} images")
                    else:
                        print(f"  ⚠️  {class_dir.name}: No images (skipping)")
        
        return sorted(non_empty_classes)
    
    def count_images(self):
        """Count images in dataset for non-empty classes only"""
        train_dir = self.dataset_dir / 'train'
        valid_dir = self.dataset_dir / 'valid'
        test_dir = self.dataset_dir / 'test'
        
        counts = {'train': 0, 'valid': 0, 'test': 0}
        
        # Only count images for classes that have training data
        classes_with_data = self.get_non_empty_classes()
        
        for split, split_dir in [('train', train_dir), ('valid', valid_dir), ('test', test_dir)]:
            if split_dir.exists():
                for class_name in classes_with_data:
                    class_dir = split_dir / class_name
                    if class_dir.exists():
                        img_count = len(list(class_dir.glob('*.*')))
                        counts[split] += img_count
        
        return counts
    
    def create_data_loaders(self):
        """Create PyTorch data loaders with only non-empty classes"""
        
        train_dir = self.dataset_dir / 'train'
        valid_dir = self.dataset_dir / 'valid'
        
        # Get classes that actually have images
        print("\n📊 Scanning for classes with images:")
        self.class_names = self.get_non_empty_classes()
        
        if len(self.class_names) == 0:
            raise ValueError("No classes with images found!")
        
        print(f"\n📚 Classes to train: {len(self.class_names)}")
        for i, class_name in enumerate(self.class_names):
            print(f"   {i}: {class_name}")
        
        # Data transformations
        train_transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.RandomRotation(20),
            transforms.RandomHorizontalFlip(),
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        val_transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Create custom datasets
        print("\n📁 Creating datasets...")
        train_dataset = BuildingDataset(train_dir, self.class_names, train_transform)
        val_dataset = BuildingDataset(valid_dir, self.class_names, val_transform)
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, 
                                  shuffle=True, num_workers=0)
        val_loader = DataLoader(val_dataset, batch_size=self.batch_size, 
                                shuffle=False, num_workers=0)
        
        print(f"\n📊 Dataset size:")
        print(f"   Train: {len(train_dataset)} images")
        print(f"   Valid: {len(val_dataset)} images")
        
        return train_loader, val_loader
    
    def create_model(self, num_classes):
        """Create transfer learning model"""
        
        # Use pre-trained ResNet50
        self.model = models.resnet50(pretrained=True)
        
        # Freeze early layers
        for param in self.model.parameters():
            param.requires_grad = False
        
        # Replace classifier head
        num_features = self.model.fc.in_features
        
        if num_classes == 1:
            # Binary classification
            self.model.fc = nn.Sequential(
                nn.Dropout(0.3),
                nn.Linear(num_features, 512),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(512, 1),
                nn.Sigmoid()
            )
            self.criterion = nn.BCELoss()
        else:
            # Multi-class classification
            self.model.fc = nn.Sequential(
                nn.Dropout(0.3),
                nn.Linear(num_features, 512),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(512, num_classes)
            )
            self.criterion = nn.CrossEntropyLoss()
        
        # Move model to GPU if available
        self.model = self.model.to(self.device)
        
        # Optimizer
        self.optimizer = optim.Adam(self.model.fc.parameters(), lr=0.001)
        
        print(f"\n✅ Model created for {num_classes} classes")
        print(f"   Using device: {self.device}")
        
        return self.model
    
    def train_epoch(self, train_loader):
        """Train one epoch"""
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(self.device), labels.to(self.device)
            
            # Zero gradients
            self.optimizer.zero_grad()
            
            # Forward pass
            outputs = self.model(inputs)
            
            if len(self.class_names) == 1:
                # Binary classification
                labels = labels.float().view(-1, 1)
                loss = self.criterion(outputs, labels)
                predicted = (outputs > 0.5).float()
                correct += (predicted == labels).sum().item()
            else:
                # Multi-class classification
                loss = self.criterion(outputs, labels)
                _, predicted = torch.max(outputs.data, 1)
                correct += (predicted == labels).sum().item()
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            # Statistics
            running_loss += loss.item()
            total += labels.size(0)
        
        epoch_loss = running_loss / len(train_loader)
        epoch_acc = 100 * correct / total
        
        return epoch_loss, epoch_acc
    
    def validate(self, val_loader):
        """Validate model"""
        self.model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                
                outputs = self.model(inputs)
                
                if len(self.class_names) == 1:
                    # Binary classification
                    labels = labels.float().view(-1, 1)
                    loss = self.criterion(outputs, labels)
                    predicted = (outputs > 0.5).float()
                    correct += (predicted == labels).sum().item()
                else:
                    # Multi-class classification
                    loss = self.criterion(outputs, labels)
                    _, predicted = torch.max(outputs.data, 1)
                    correct += (predicted == labels).sum().item()
                
                running_loss += loss.item()
                total += labels.size(0)
        
        val_loss = running_loss / len(val_loader)
        val_acc = 100 * correct / total
        
        return val_loss, val_acc
    
    def train(self, epochs=50):
        """Train the model"""
        
        print("\n" + "="*60)
        print("  BUILDING RECOGNITION - PYTORCH TRAINING")
        print("="*60)
        
        # Check GPU
        self.check_gpu()
        
        # Count images
        counts = self.count_images()
        print(f"\n📊 Dataset split:")
        print(f"  Train: {counts['train']} images")
        print(f"  Valid: {counts['valid']} images")
        print(f"  Test: {counts['test']} images")
        
        if counts['train'] == 0:
            print("\n❌ No training images found!")
            return None
        
        # Create data loaders
        print("\n📁 Creating data loaders...")
        try:
            train_loader, val_loader = self.create_data_loaders()
        except Exception as e:
            print(f"❌ Error creating data loaders: {e}")
            return None
        
        # Create model
        print("\n🏗️  Creating model...")
        self.create_model(len(self.class_names))
        
        # Training loop
        print(f"\n🚀 Starting training ({epochs} epochs)...")
        print("-" * 60)
        
        best_val_acc = 0
        
        for epoch in range(epochs):
            # Train
            train_loss, train_acc = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)
            
            # Store history
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            
            # Print progress
            print(f"Epoch {epoch+1}/{epochs}")
            print(f"  Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
            print(f"  Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(self.model.state_dict(), 'best_model.pth')
                print(f"  ✅ Best model saved! (Val Acc: {val_acc:.2f}%)")
            
            print()
        
        # Load best model
        self.model.load_state_dict(torch.load('best_model.pth'))
        
        print(f"\n✅ Training completed!")
        print(f"🏆 Best validation accuracy: {best_val_acc:.2f}%")
        
        return self.history
    
    def save_model(self, name='building_recognizer'):
        """Save model in multiple formats"""
        
        # Save PyTorch model
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'class_names': self.class_names,
            'img_size': self.img_size,
            'device': str(self.device),
            'num_classes': len(self.class_names)
        }, f'{name}.pth')
        print(f"✅ PyTorch model saved: {name}.pth")
        
        # Save class names
        with open(f'{name}_classes.json', 'w') as f:
            json.dump(self.class_names, f)
        print(f"✅ Classes saved: {name}_classes.json")
        
        # Save class mapping
        class_mapping = {name: idx for idx, name in enumerate(self.class_names)}
        with open(f'{name}_mapping.json', 'w') as f:
            json.dump(class_mapping, f)
        print(f"✅ Class mapping saved: {name}_mapping.json")
        
        # Convert to TorchScript (for production)
        self.model.eval()
        example_input = torch.randn(1, 3, self.img_size, self.img_size).to(self.device)
        try:
            traced_model = torch.jit.trace(self.model, example_input)
            traced_model.save(f'{name}_scripted.pt')
            print(f"✅ TorchScript model saved: {name}_scripted.pt")
        except Exception as e:
            print(f"⚠️  Could not convert to TorchScript: {e}")
    
    def plot_history(self):
        """Plot training history"""
        
        if not self.history['train_loss']:
            print("⚠️  No training history available")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        
        # Accuracy
        axes[0].plot(self.history['train_acc'], label='Training')
        axes[0].plot(self.history['val_acc'], label='Validation')
        axes[0].set_title('Model Accuracy')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Accuracy (%)')
        axes[0].legend()
        axes[0].grid(True)
        
        # Loss
        axes[1].plot(self.history['train_loss'], label='Training')
        axes[1].plot(self.history['val_loss'], label='Validation')
        axes[1].set_title('Model Loss')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Loss')
        axes[1].legend()
        axes[1].grid(True)
        
        plt.tight_layout()
        plt.savefig('training_history.png', dpi=300, bbox_inches='tight')
        print("📈 Training plots saved: training_history.png")
    
    def test_model(self):
        """Test model on test set"""
        
        test_dir = self.dataset_dir / 'test'
        
        if not test_dir.exists():
            print("⚠️  No test directory found")
            return
        
        print("\n📊 Testing on test set...")
        
        # Test transformations
        test_transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Create test dataset
        test_dataset = BuildingDataset(test_dir, self.class_names, test_transform)
        
        if len(test_dataset) == 0:
            print("⚠️  No test images found for trained classes")
            return
        
        test_loader = DataLoader(test_dataset, batch_size=self.batch_size, 
                                shuffle=False, num_workers=0)
        
        # Evaluate
        self.model.eval()
        all_preds = []
        all_labels = []
        all_probs = []
        
        with torch.no_grad():
            for inputs, labels in test_loader:
                inputs = inputs.to(self.device)
                outputs = self.model(inputs)
                
                if len(self.class_names) == 1:
                    # Binary classification
                    probs = outputs.cpu().numpy()
                    preds = (outputs > 0.5).int().cpu().numpy()
                    all_probs.extend(probs.flatten())
                    all_preds.extend(preds.flatten())
                    all_labels.extend(labels.numpy())
                else:
                    # Multi-class classification
                    _, preds = torch.max(outputs, 1)
                    all_preds.extend(preds.cpu().numpy())
                    all_labels.extend(labels.numpy())
        
        # Calculate accuracy
        accuracy = 100 * np.sum(np.array(all_preds) == np.array(all_labels)) / len(all_labels)
        print(f"\n✅ Test Accuracy: {accuracy:.2f}%")
        
        if len(self.class_names) == 1:
            # Binary classification metrics
            from sklearn.metrics import precision_score, recall_score, f1_score
            precision = precision_score(all_labels, all_preds, zero_division=0)
            recall = recall_score(all_labels, all_preds, zero_division=0)
            f1 = f1_score(all_labels, all_preds, zero_division=0)
            
            print(f"\n📊 Binary Classification Metrics:")
            print(f"   Precision: {precision:.4f}")
            print(f"   Recall: {recall:.4f}")
            print(f"   F1-Score: {f1:.4f}")
            
            # Plot prediction probabilities
            plt.figure(figsize=(10, 6))
            plt.hist([all_probs[i] for i in range(len(all_probs)) if all_labels[i] == 1], 
                    alpha=0.5, label='CEAT', bins=20)
            plt.hist([all_probs[i] for i in range(len(all_probs)) if all_labels[i] == 0], 
                    alpha=0.5, label='Not CEAT', bins=20)
            plt.xlabel('Predicted Probability')
            plt.ylabel('Count')
            plt.title('Prediction Probabilities on Test Set')
            plt.legend()
            plt.savefig('prediction_distribution.png', dpi=300)
            print("📊 Prediction distribution saved: prediction_distribution.png")
        
        elif len(self.class_names) > 1:
            # Multi-class classification report
            print("\n📊 Classification Report:")
            print(classification_report(all_labels, all_preds, 
                                       target_names=self.class_names))
            
            # Confusion matrix
            cm = confusion_matrix(all_labels, all_preds)
            plt.figure(figsize=(10, 8))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                       xticklabels=self.class_names,
                       yticklabels=self.class_names)
            plt.title('Confusion Matrix')
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            plt.tight_layout()
            plt.savefig('confusion_matrix.png', dpi=300)
            print("📊 Confusion matrix saved: confusion_matrix.png")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║     BUILDING RECOGNITION - PYTORCH WITH GPU SUPPORT         ║
║     Custom dataset loader - only uses folders with images   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize trainer
    trainer = BuildingTrainer(dataset_dir='dataset', batch_size=32)
    
    # Train
    history = trainer.train(epochs=50)
    
    if history:
        # Test on test set
        trainer.test_model()
        
        # Save model
        trainer.save_model()
        
        # Plot results
        trainer.plot_history()
        
        print("\n" + "="*60)
        print("  ✅ TRAINING COMPLETE!")
        print("="*60)
        print("\n📁 Files created:")
        print("  - best_model.pth (best model checkpoint)")
        print("  - building_recognizer.pth (final model)")
        print("  - building_recognizer_classes.json (class names)")
        print("  - building_recognizer_mapping.json (class to index mapping)")
        print("  - building_recognizer_scripted.pt (production ready)")
        print("  - training_history.png")
        print("  - prediction_distribution.png (for binary classifier)")
        
        print("\n📝 Next steps:")
        print("  1. Add more building images to dataset/train/[building_name]/")
        print("  2. Run this script again to retrain with all buildings")
        print("  3. The model will automatically include new classes")
        print("\n🔍 To use the model for prediction:")
        print("  from train_roboflow import BuildingTrainer")
        print("  trainer = BuildingTrainer()")
        print("  trainer.load_model('building_recognizer.pth')")
        print("  # Then use trainer.predict('image.jpg')")
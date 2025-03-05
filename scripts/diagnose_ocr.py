"""
Script de diagnostic pour vérifier les installations OCR et les exécuter directement.
"""
import os
import sys
import subprocess
import asyncio
from pathlib import Path
import shutil
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("❌ PIL/Pillow non installé. Installer avec: pip install Pillow")

# Ajouter le chemin parent au PATH pour pouvoir importer les modules de l'application
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importer la configuration depuis dotenv
from dotenv import load_dotenv
load_dotenv()

# Chemins des dépendances - chargés depuis les variables d'environnement
TESSERACT_PATH = os.environ.get("TESSERACT_PATH", r"C:\Users\aurel\AppData\Local\Programs\Tesseract-OCR")
POPPLER_PATH = os.environ.get("POPPLER_PATH", r"C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin")
GS_PATH = os.environ.get("GHOSTSCRIPT_PATH", r"C:\ProgramData\chocolatey\lib-bad\Ghostscript.app\10.4.0\tools")

def check_path(name, path):
    """Vérifie si un chemin existe et contient les fichiers attendus."""
    if not Path(path).exists():
        print(f"❌ {name}: Le chemin {path} n'existe pas")
        return False

    print(f"✅ {name}: Le chemin {path} existe")
    return True

def check_command(name, cmd):
    """Vérifie si une commande est disponible."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"✅ {name} est disponible")
        # Corriger l'erreur de syntaxe en évitant le caractère d'échappement dans la f-string
        first_line = result.stdout.strip().split('\n')[0] if result.stdout else ""
        print(f"   Version: {first_line}")
        return True
    except FileNotFoundError:
        print(f"❌ {name} n'est pas disponible")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la vérification de {name}: {str(e)}")
        return False

async def run_ocrmypdf(input_file, output_file):
    """Exécute OCRmyPDF avec sortie détaillée."""
    # Ajouter les chemins au PATH
    env = os.environ.copy()
    env["PATH"] = f"{TESSERACT_PATH}{os.pathsep}{POPPLER_PATH}{os.pathsep}{GS_PATH}{os.pathsep}{env['PATH']}"
    
    try:
        # Commande de diagnostic
        print(f"\n=== Exécution de la commande OCRmyPDF sur {input_file} ===")
        print(f"Sortie vers: {output_file}")
        
        # Vérifier que le fichier d'entrée existe
        if not Path(input_file).exists():
            print(f"❌ Le fichier d'entrée n'existe pas: {input_file}")
            return
            
        # Version simplifiée (juste pour tester)
        cmd = [
            "ocrmypdf",
            "--verbose",  # Plus de détails
            "--skip-text",
            "--language", "fra",
            input_file,
            output_file
        ]
        
        print(f"Commande: {' '.join(cmd)}")
        
        # Exécuter la commande de manière asynchrone
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        print(f"\nCode de retour: {process.returncode}")
        print("\n=== STDOUT ===")
        print(stdout.decode())
        print("\n=== STDERR ===")
        print(stderr.decode())
        
        if process.returncode == 0:
            print("\n✅ OCRmyPDF a réussi!")
        else:
            print(f"\n❌ OCRmyPDF a échoué avec le code {process.returncode}")
            
    except Exception as e:
        print(f"❌ Exception lors de l'exécution d'OCRmyPDF: {str(e)}")

def create_test_image():
    """Crée une image de test pour Tesseract."""
    if not PIL_AVAILABLE:
        return None
        
    # Créer une image avec du texte
    img = Image.new('RGB', (400, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Utiliser une police par défaut
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    d.text((10, 40), "Test Tesseract OCR - TechnicIA", fill=(0, 0, 0), font=font)
    
    # Sauvegarder l'image
    img_path = Path("test_tesseract.png")
    img.save(img_path)
    
    return img_path

async def test_tesseract_directly():
    """Teste Tesseract directement avec une image."""
    try:
        print("\n=== Test de Tesseract directement ===")
        tesseract_exe = Path(TESSERACT_PATH) / "tesseract.exe"
        
        # Ajouter Tesseract au PATH temporairement
        env = os.environ.copy()
        env["PATH"] = f"{TESSERACT_PATH}{os.pathsep}{env['PATH']}"
        
        # Créer une image de test
        img_path = create_test_image()
        if not img_path:
            print("❌ Impossible de créer une image de test. PIL/Pillow est requis.")
            return
            
        print(f"Image de test créée: {img_path}")
        
        # Tester avec tesseract
        cmd = [
            str(tesseract_exe),
            str(img_path),
            "temp_output"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        print(f"Code de retour: {process.returncode}")
        print("STDOUT:", stdout.decode())
        print("STDERR:", stderr.decode())
        
        # Vérifier les résultats
        output_file = Path("temp_output.txt")
        if output_file.exists():
            content = output_file.read_text()
            print(f"Contenu du fichier de sortie: {content}")
            output_file.unlink()
            if "Test Tesseract OCR" in content:
                print("✅ Tesseract a correctement reconnu le texte!")
            else:
                print("⚠️ Tesseract n'a pas reconnu le texte correctement.")
        else:
            print("❌ Fichier de sortie non trouvé.")
        
        # Nettoyer
        if img_path.exists():
            img_path.unlink()
        
    except Exception as e:
        print(f"❌ Exception lors du test de Tesseract: {str(e)}")

async def main():
    print("=== DIAGNOSTIC OCR ===")
    
    # 1. Vérifier les chemins
    print("\n=== VÉRIFICATION DES CHEMINS ===")
    check_path("Tesseract", TESSERACT_PATH)
    check_path("Poppler", POPPLER_PATH)
    check_path("Ghostscript", GS_PATH)
    
    # Vérifier les fichiers spécifiques dans les dossiers
    tesseract_exe = Path(TESSERACT_PATH) / "tesseract.exe"
    if tesseract_exe.exists():
        print(f"✅ Fichier exécutable tesseract.exe trouvé: {tesseract_exe}")
    else:
        print(f"❌ Fichier exécutable tesseract.exe NON trouvé dans {TESSERACT_PATH}")
    
    # 2. Vérifier les exécutables
    print("\n=== VÉRIFICATION DES EXÉCUTABLES ===")
    
    # PATH temporaire pour les tests
    old_path = os.environ["PATH"]
    os.environ["PATH"] = f"{TESSERACT_PATH}{os.pathsep}{POPPLER_PATH}{os.pathsep}{GS_PATH}{os.pathsep}{old_path}"
    
    check_command("Tesseract", ["tesseract", "--version"])
    check_command("Poppler (pdfinfo)", ["pdfinfo", "-v"])
    
    # Recherche des exécutables Ghostscript
    try:
        gs_exes = list(Path(GS_PATH).glob("gs*.exe"))
        if gs_exes:
            check_command("Ghostscript", [str(gs_exes[0]), "-v"])
        else:
            print("❌ Aucun exécutable Ghostscript trouvé")
            
            # Chercher dans le Path système
            system_gs = shutil.which("gswin64c.exe") or shutil.which("gswin32c.exe") or shutil.which("gs.exe")
            if system_gs:
                print(f"✅ Ghostscript trouvé dans le PATH système: {system_gs}")
                check_command("Ghostscript (système)", [system_gs, "-v"])
            else:
                print("❌ Ghostscript non trouvé dans le PATH système")
    except Exception as e:
        print(f"❌ Erreur lors de la recherche de Ghostscript: {str(e)}")
    
    check_command("OCRmyPDF", ["ocrmypdf", "--version"])
    
    # 3. Test de Tesseract directement
    await test_tesseract_directly()
    
    # 4. Test OCRmyPDF
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = f"ocr_output_{Path(input_file).name}"
        await run_ocrmypdf(input_file, output_file)
    else:
        print("\nPour tester OCRmyPDF, fournissez un fichier PDF en argument:")
        print(f"python {Path(__file__).name} chemin/vers/fichier.pdf")
    
    # Restaurer le PATH
    os.environ["PATH"] = old_path

if __name__ == "__main__":
    asyncio.run(main())

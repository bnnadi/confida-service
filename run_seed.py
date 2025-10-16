#!/usr/bin/env python3
"""
Simple script to run the seed data for local development.
"""

import subprocess
import sys
import os

def main():
    """Run the seed data script."""
    print("🌱 Running database seed data script...")
    
    try:
        # Change to the project directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Run the seed data script
        result = subprocess.run([sys.executable, "seed_data.py"], check=True)
        
        print("✅ Seed data script completed successfully!")
        print("\n📋 Next steps:")
        print("1. Start the application: uvicorn app.main:app --reload")
        print("2. Test with demo accounts:")
        print("   - demo@confida.com / demo123456")
        print("   - john.doe@example.com / password123")
        print("   - jane.smith@example.com / password123")
        print("   - admin@confida.com / admin123456")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running seed data script: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

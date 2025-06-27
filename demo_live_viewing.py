#!/usr/bin/env python3

"""
Demo script for live LibreOffice document viewing and editing
This shows how to see changes in real-time as you modify documents via MCP
"""

import asyncio
import tempfile
import time
from pathlib import Path

# Import the MCP functions
from libremcp import (
    create_document,
    insert_text_at_position,
    open_document_in_libreoffice,
    create_live_editing_session,
    watch_document_changes,
    refresh_document_in_libreoffice,
    read_document_text
)

async def demo_live_viewing():
    """Demonstrate live viewing of document changes"""
    
    print("🚀 LibreOffice Live Viewing Demo")
    print("=" * 50)
    print("This demo shows how to see changes live in LibreOffice while editing via MCP")
    print("")
    
    # Create a temporary document
    temp_dir = Path(tempfile.mkdtemp())
    demo_doc = temp_dir / "live_demo.odt"
    
    try:
        # 1. Create initial document
        print("📝 Step 1: Creating initial document...")
        result = create_document(str(demo_doc), "writer", """Live Editing Demo Document

This document will be modified via MCP while you watch in LibreOffice GUI.

Current sections:
- Introduction (this section)
- Content will be added below...

""")
        print(f"✅ Created: {result.filename}")
        
        # 2. Start live editing session
        print("\n🖥️  Step 2: Opening document in LibreOffice GUI...")
        session = create_live_editing_session(str(demo_doc), auto_refresh=True)
        print(f"✅ Live session started: {session['session_id']}")
        print(f"📖 Document opened in LibreOffice: {demo_doc.name}")
        
        # Give user time to see the document open
        print("\n⏳ Waiting 5 seconds for LibreOffice to open...")
        print("   💡 You should see the document open in LibreOffice GUI now!")
        time.sleep(5)
        
        # 3. Start making live changes
        print("\n✏️  Step 3: Making live changes via MCP...")
        
        changes = [
            ("Adding methodology section...", """
Methodology Section (Added via MCP)

This section was automatically added while you were watching!

Research approach:
1. Document creation via MCP
2. Live editing demonstration  
3. Real-time change observation
4. Automatic refresh testing

"""),
            ("Adding results section...", """
Results Section (Added via MCP)

Key findings from the live editing demo:
- ✅ MCP can modify documents in real-time
- ✅ LibreOffice can detect file changes
- ✅ Users can see updates live in the GUI
- ✅ Seamless integration between MCP and LibreOffice

Performance metrics:
- Change detection: < 1 second
- UI refresh: Automatic on file save
- User experience: Smooth and intuitive

"""),
            ("Adding conclusion...", """
Conclusion (Added via MCP)

This demonstration successfully shows:

1. 🔄 Real-time document editing via MCP
2. 👀 Live viewing in LibreOffice GUI  
3. 🚀 Seamless integration between AI and document editing
4. ⚡ Fast change detection and refresh

The LibreOffice MCP server enables powerful document automation
while maintaining full visual feedback for users!

--- Demo Complete ---

""")
        ]
        
        for i, (description, content) in enumerate(changes, 1):
            print(f"\n   📝 Change {i}: {description}")
            
            # Make the change via MCP
            insert_text_at_position(str(demo_doc), content, "end")
            
            # Send refresh signal
            refresh_result = refresh_document_in_libreoffice(str(demo_doc))
            if refresh_result["success"]:
                print(f"   🔄 Refresh signal sent")
            
            print(f"   💡 Check LibreOffice GUI - you should see the new content!")
            print(f"   📋 If not visible, press Ctrl+Shift+R to reload in LibreOffice")
            
            # Wait between changes
            wait_time = 8
            print(f"   ⏳ Waiting {wait_time} seconds before next change...")
            time.sleep(wait_time)
        
        # 4. Show final document stats
        print("\n📊 Step 4: Final document statistics...")
        final_content = read_document_text(str(demo_doc))
        print(f"✅ Final document:")
        print(f"   📝 Words: {final_content.word_count}")
        print(f"   🔤 Characters: {final_content.char_count}")
        print(f"   📄 File size: {Path(demo_doc).stat().st_size} bytes")
        
        # 5. Watch for additional changes
        print("\n👀 Step 5: Watching for manual changes...")
        print("   💡 Try editing the document manually in LibreOffice GUI!")
        print("   📝 Add some text, then save (Ctrl+S)")
        print("   🔍 We'll detect your changes...")
        
        watch_result = watch_document_changes(str(demo_doc), duration_seconds=15)
        if watch_result["changes_detected"] > 0:
            print(f"✅ Detected {watch_result['changes_detected']} manual changes!")
            for change in watch_result["changes"]:
                print(f"   📝 {change['timestamp']}: {change['size_change']:+d} bytes")
        else:
            print("   ℹ️  No manual changes detected")
        
        print(f"\n🎉 Live viewing demo completed!")
        print(f"📁 Demo document: {demo_doc}")
        print(f"💡 The document remains open in LibreOffice for further exploration")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        
    finally:
        # Note: We don't delete the temp file so user can continue exploring
        print(f"\n📂 Demo files preserved in: {temp_dir}")
        print("   🗑️  You can delete this directory when done exploring")

def main():
    """Main demo function"""
    print("🌟 LibreOffice MCP Server - Live Viewing Capabilities")
    print("=" * 60)
    print("")
    print("This demo will:")
    print("1. 📝 Create a document")
    print("2. 🖥️  Open it in LibreOffice GUI")
    print("3. ✏️  Make live changes via MCP")
    print("4. 👀 Show you the changes in real-time")
    print("5. 🔍 Watch for your manual edits")
    print("")
    
    try:
        # Check if LibreOffice GUI is available
        import subprocess
        result = subprocess.run(['libreoffice', '--version'], 
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            print("❌ LibreOffice not found. Please install LibreOffice first.")
            return
    except Exception:
        print("❌ LibreOffice not available. Please install LibreOffice first.")
        return
    
    print("✅ LibreOffice detected. Starting demo...")
    print("")
    
    asyncio.run(demo_live_viewing())
    
    print("\n" + "=" * 60)
    print("💡 How to use live viewing with Claude Desktop:")
    print("")
    print("1. 🖥️  Open a document:")
    print('   "Open my document.odt in LibreOffice for live viewing"')
    print("")
    print("2. ✏️  Make changes:")
    print('   "Add a new paragraph to my document"')
    print('   "Insert a table at the end of the document"')
    print("")
    print("3. 🔄 Refresh if needed:")
    print('   "Refresh the document in LibreOffice"')
    print("")
    print("4. 👀 Watch changes:")
    print('   "Watch my document for changes for 30 seconds"')
    print("")
    print("📚 See EXAMPLES.md for more live viewing examples!")

if __name__ == "__main__":
    main()

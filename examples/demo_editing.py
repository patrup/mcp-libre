#!/usr/bin/env python3

"""
Demo script showing how to edit LibreOffice documents using the MCP server
This demonstrates the capabilities that would be available through ChatGPT 
if it supported MCP (currently only works with Claude Desktop and Super Assistant)
"""

import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Import the MCP server functions directly
from libremcp import (
    create_document, 
    read_document_text, 
    insert_text_at_position,
    get_document_statistics,
    convert_document
)

async def demo_document_editing():
    """Demonstrate document editing capabilities"""
    
    print("🚀 LibreOffice MCP Server - Document Editing Demo")
    print("=" * 50)
    
    # Create a temporary directory for our demo
    temp_dir = Path(tempfile.mkdtemp())
    doc_path = temp_dir / "demo_document.odt"
    
    try:
        # 1. Create a new Writer document
        print("\n📝 Step 1: Creating a new Writer document...")
        initial_content = """Project Report

This is the introduction to our project report.

Current sections:
- Introduction
- Methodology (to be added)
- Results (to be added)
- Conclusion (to be added)
"""
        
        result = create_document(str(doc_path), "writer", initial_content)
        print(f"✅ Created document: {result.path}")
        print(f"   Content preview: {initial_content[:100]}...")
        
        # 2. Read the document content
        print("\n📖 Step 2: Reading document content...")
        content = read_document_text(str(doc_path))
        print(f"✅ Document contains {content.word_count} words, {content.char_count} characters")
        
        # 3. Add content to the document (simulate editing)
        print("\n✏️  Step 3: Adding methodology section...")
        methodology_text = """

Methodology

Our research methodology included the following steps:
1. Literature review of existing solutions
2. Requirements gathering from stakeholders  
3. Design and prototyping phase
4. Implementation and testing
5. Evaluation and feedback collection

This systematic approach ensured comprehensive coverage of all project aspects.
"""
        
        edit_result = insert_text_at_position(str(doc_path), methodology_text, "end")
        print(f"✅ Added methodology section")
        print(f"   New word count: {edit_result.word_count} words")
        
        # 4. Add results section
        print("\n📊 Step 4: Adding results section...")
        results_text = """

Results

The project yielded the following key results:

Performance Metrics:
- Processing speed: 95% improvement over baseline
- Accuracy rate: 98.5% on test dataset
- User satisfaction: 4.7/5.0 average rating

Technical Achievements:
- Successfully integrated LibreOffice with MCP protocol
- Implemented 10+ document manipulation tools
- Created comprehensive documentation and examples

These results demonstrate the effectiveness of our approach.
"""
        
        edit_result = insert_text_at_position(str(doc_path), results_text, "end")
        print(f"✅ Added results section")
        print(f"   New word count: {edit_result.word_count} words")
        
        # 5. Add conclusion
        print("\n🎯 Step 5: Adding conclusion...")
        conclusion_text = """

Conclusion

This project successfully demonstrates the integration of LibreOffice document 
processing capabilities with AI assistants through the Model Context Protocol.

Key accomplishments include:
- Seamless document creation and editing
- Support for multiple file formats
- Robust error handling and user feedback
- Comprehensive testing and documentation

Future work will focus on expanding format support and adding collaborative 
editing features. The foundation established here provides a solid platform 
for continued development and enhancement.

--- End of Report ---
"""
        
        edit_result = insert_text_at_position(str(doc_path), conclusion_text, "end")
        print(f"✅ Added conclusion section")
        print(f"   Final word count: {edit_result.word_count} words")
        
        # 6. Get final document statistics
        print("\n📈 Step 6: Getting document statistics...")
        stats = get_document_statistics(str(doc_path))
        print(f"✅ Final document statistics:")
        print(f"   📝 Words: {stats['content_stats']['word_count']}")
        print(f"   📄 Pages: {stats['content_stats']['page_count']}")
        print(f"   🔤 Characters: {stats['content_stats']['char_count']}")
        print(f"   📑 Paragraphs: {stats['content_stats']['paragraph_count']}")
        
        # 7. Convert to different formats
        print("\n🔄 Step 7: Converting to different formats...")
        
        # Convert to text file
        txt_path = temp_dir / "demo_document.txt"
        convert_result = convert_document(str(doc_path), str(txt_path), "txt")
        if convert_result['success']:
            print(f"✅ Converted to TXT: {txt_path}")
        
        # Try to convert to PDF (might fail without Java)
        pdf_path = temp_dir / "demo_document.pdf"
        convert_result = convert_document(str(doc_path), str(pdf_path), "pdf")
        if convert_result['success']:
            print(f"✅ Converted to PDF: {pdf_path}")
        else:
            print(f"⚠️  PDF conversion failed (Java required): {convert_result.get('error', 'Unknown error')}")
        
        # 8. Show final content
        print("\n📖 Step 8: Final document content preview...")
        final_content = read_document_text(str(doc_path))
        lines = final_content.content.split('\n')
        print("📄 Document structure:")
        for i, line in enumerate(lines[:20], 1):  # Show first 20 lines
            if line.strip():
                print(f"   {i:2d}: {line.strip()}")
        
        if len(lines) > 20:
            print(f"   ... and {len(lines) - 20} more lines")
        
        print(f"\n✨ Demo completed successfully!")
        print(f"📁 Demo files created in: {temp_dir}")
        print(f"🗂️  Files: {list(temp_dir.glob('*'))}")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        
    finally:
        # Optionally clean up (comment out to keep files for inspection)
        # import shutil
        # shutil.rmtree(temp_dir)
        pass

def main():
    """Main demo function"""
    print("This demo shows what document editing would look like through ChatGPT")
    print("if ChatGPT supported MCP servers (currently only Claude Desktop and Super Assistant do)")
    print("")
    
    asyncio.run(demo_document_editing())
    
    print("\n" + "=" * 60)
    print("🔗 How to actually use these capabilities:")
    print("")
    print("1. 📱 Claude Desktop:")
    print("   - Already configured in claude_config.json")
    print("   - Just ask: 'Edit my document and add a conclusion'")
    print("")
    print("2. 🌐 Super Assistant (Browser):")
    print("   - Run: ./mcp-helper.sh proxy")
    print("   - Configure extension to use http://localhost:3006")
    print("   - Ask: 'Edit this Writer document'")
    print("")
    print("3. ❌ ChatGPT Browser:")
    print("   - Not supported (no MCP integration)")
    print("   - See CHATGPT_BROWSER_GUIDE.md for alternatives")
    print("")

if __name__ == "__main__":
    main()

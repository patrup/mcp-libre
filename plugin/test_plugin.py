#!/usr/bin/env python3
"""
LibreOffice MCP Extension Test Client

This script tests the HTTP API functionality of the LibreOffice MCP extension.
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional

class LibreOfficeMCPClient:
    """Test client for LibreOffice MCP Extension HTTP API"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """Initialize the test client"""
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "LibreOffice-MCP-Test-Client/1.0"
        })
    
    def test_connection(self) -> bool:
        """Test if the MCP server is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server is healthy: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to server: {e}")
            return False
    
    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information"""
        try:
            response = self.session.get(f"{self.base_url}/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get server info: {e}")
            return None
    
    def list_tools(self) -> Optional[Dict[str, Any]]:
        """List available tools"""
        try:
            response = self.session.get(f"{self.base_url}/tools")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to list tools: {e}")
            return None
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Execute a specific tool"""
        if parameters is None:
            parameters = {}
        
        try:
            # Method 1: Direct tool endpoint
            response = self.session.post(
                f"{self.base_url}/tools/{tool_name}",
                json=parameters
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to execute tool {tool_name}: {e}")
            try:
                # Method 2: Generic execute endpoint
                response = self.session.post(
                    f"{self.base_url}/execute",
                    json={"tool": tool_name, "parameters": parameters}
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e2:
                print(f"❌ Also failed with generic endpoint: {e2}")
                return None
    
    def run_comprehensive_test(self):
        """Run a comprehensive test of all functionality"""
        print("🧪 LibreOffice MCP Extension Test Suite")
        print("=" * 50)
        
        # Test 1: Connection
        print("\n1️⃣ Testing connection...")
        if not self.test_connection():
            print("❌ Cannot proceed without server connection")
            return False
        
        # Test 2: Server info
        print("\n2️⃣ Getting server information...")
        server_info = self.get_server_info()
        if server_info:
            print(f"✅ Server: {server_info.get('name', 'Unknown')}")
            print(f"   Version: {server_info.get('version', 'Unknown')}")
            print(f"   Tools: {server_info.get('tools_count', 0)}")
        else:
            print("❌ Failed to get server info")
        
        # Test 3: List tools
        print("\n3️⃣ Listing available tools...")
        tools_info = self.list_tools()
        if tools_info:
            tools = tools_info.get('tools', [])
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        else:
            print("❌ Failed to list tools")
            return False
        
        # Test 4: Document info (should work even with no document)
        print("\n4️⃣ Testing get_document_info_live...")
        result = self.execute_tool("get_document_info_live")
        if result:
            if result.get('success'):
                print("✅ Document info retrieved successfully")
                doc_info = result.get('document_info', {})
                print(f"   Document type: {doc_info.get('type', 'Unknown')}")
                print(f"   Title: {doc_info.get('title', 'Unknown')}")
            else:
                print(f"⚠️  No active document (expected): {result.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to get document info")
        
        # Test 5: Create document
        print("\n5️⃣ Testing document creation...")
        result = self.execute_tool("create_document_live", {"doc_type": "writer"})
        if result and result.get('success'):
            print("✅ Created new Writer document")
            time.sleep(1)  # Give LibreOffice time to open the document
        else:
            print(f"❌ Failed to create document: {result.get('error') if result else 'No response'}")
        
        # Test 6: Insert text (if document was created)
        print("\n6️⃣ Testing text insertion...")
        test_text = "Hello from LibreOffice MCP Extension test! 🎉"
        result = self.execute_tool("insert_text_live", {"text": test_text})
        if result and result.get('success'):
            print(f"✅ Inserted text: '{test_text}'")
        else:
            print(f"❌ Failed to insert text: {result.get('error') if result else 'No response'}")
        
        # Test 7: Get document info again (should show the new document)
        print("\n7️⃣ Testing document info after creation...")
        result = self.execute_tool("get_document_info_live")
        if result and result.get('success'):
            print("✅ Document info retrieved after creation")
            doc_info = result.get('document_info', {})
            print(f"   Type: {doc_info.get('type', 'Unknown')}")
            print(f"   Modified: {doc_info.get('modified', False)}")
            print(f"   Character count: {doc_info.get('character_count', 0)}")
        else:
            print(f"❌ Failed to get updated document info: {result.get('error') if result else 'No response'}")
        
        # Test 8: List open documents
        print("\n8️⃣ Testing list_open_documents...")
        result = self.execute_tool("list_open_documents")
        if result and result.get('success'):
            docs = result.get('documents', [])
            print(f"✅ Found {len(docs)} open document(s)")
            for i, doc in enumerate(docs):
                print(f"   {i+1}. {doc.get('title', 'Untitled')} ({doc.get('type', 'unknown')})")
        else:
            print(f"❌ Failed to list open documents: {result.get('error') if result else 'No response'}")
        
        # Test 9: Get text content
        print("\n9️⃣ Testing text content extraction...")
        result = self.execute_tool("get_text_content_live")
        if result and result.get('success'):
            content = result.get('content', '')
            print(f"✅ Extracted {len(content)} characters")
            print(f"   Preview: '{content[:50]}{'...' if len(content) > 50 else ''}'")
        else:
            print(f"❌ Failed to get text content: {result.get('error') if result else 'No response'}")
        
        print("\n🎉 Test suite completed!")
        print("\n💡 Tips:")
        print("   - Make sure LibreOffice is running with the extension installed")
        print("   - The extension auto-starts the MCP server on localhost:8765")
        print("   - Check Tools > MCP Server in LibreOffice for manual control")
        
        return True
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("🎮 LibreOffice MCP Extension Interactive Test Client")
        print("=" * 55)
        
        if not self.test_connection():
            print("❌ Cannot start interactive mode without server connection")
            return
        
        # List available tools
        tools_info = self.list_tools()
        if not tools_info:
            print("❌ Cannot get tools list")
            return
        
        tools = {tool['name']: tool for tool in tools_info.get('tools', [])}
        tool_names = list(tools.keys())
        
        print(f"\n📋 Available tools ({len(tool_names)}):")
        for i, name in enumerate(tool_names):
            print(f"   {i+1}. {name}")
        
        while True:
            try:
                print("\n" + "─" * 40)
                choice = input("Enter tool number (or 'quit'): ").strip()
                
                if choice.lower() in ['quit', 'exit', 'q']:
                    break
                
                try:
                    tool_index = int(choice) - 1
                    if 0 <= tool_index < len(tool_names):
                        tool_name = tool_names[tool_index]
                        tool_info = tools[tool_name]
                        
                        print(f"\n🔧 Tool: {tool_name}")
                        print(f"Description: {tool_info.get('description', 'No description')}")
                        
                        # Get parameters
                        parameters = {}
                        tool_params = tool_info.get('parameters', {}).get('properties', {})
                        required_params = tool_info.get('parameters', {}).get('required', [])
                        
                        if tool_params:
                            print("\nParameters:")
                            for param_name, param_info in tool_params.items():
                                param_type = param_info.get('type', 'string')
                                param_desc = param_info.get('description', 'No description')
                                param_default = param_info.get('default', '')
                                is_required = param_name in required_params
                                
                                prompt = f"  {param_name} ({param_type})" + \
                                        (f" [required]" if is_required else f" [default: {param_default}]") + \
                                        f": "
                                
                                value = input(prompt).strip()
                                
                                if value:
                                    # Try to convert to appropriate type
                                    if param_type == 'integer':
                                        try:
                                            parameters[param_name] = int(value)
                                        except ValueError:
                                            print(f"⚠️  Invalid integer: {value}")
                                            continue
                                    elif param_type == 'boolean':
                                        parameters[param_name] = value.lower() in ['true', '1', 'yes', 'on']
                                    else:
                                        parameters[param_name] = value
                                elif is_required:
                                    print(f"⚠️  Required parameter {param_name} cannot be empty")
                                    continue
                        
                        # Execute tool
                        print(f"\n⚡ Executing {tool_name}...")
                        result = self.execute_tool(tool_name, parameters)
                        
                        if result:
                            print(f"\n📊 Result:")
                            print(json.dumps(result, indent=2))
                        else:
                            print("❌ No result returned")
                    
                    else:
                        print(f"❌ Invalid tool number: {choice}")
                
                except ValueError:
                    print(f"❌ Invalid input: {choice}")
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main function"""
    client = LibreOfficeMCPClient()
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        client.interactive_mode()
    else:
        client.run_comprehensive_test()


if __name__ == "__main__":
    main()

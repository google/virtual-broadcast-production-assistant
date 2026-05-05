"""
Utility module for retrieving skills from MCP server tools.
"""
import logging
from typing import List
from a2a.types import AgentSkill

logger = logging.getLogger(__name__)


def tool_to_skill(tool) -> AgentSkill:
    """
    Convert an MCP tool definition to an AgentSkill.
    
    Args:
        tool: MCP tool definition (can be a dict or MCPTool object)
        
    Returns:
        AgentSkill object
    """
    # Handle both dictionary and MCPTool object formats
    if hasattr(tool, '__dict__'):
        # It's an MCPTool object, access attributes directly
        tool_name = getattr(tool, 'name', '') or getattr(tool, 'id', '')
        tool_description = getattr(tool, 'description', f'Tool: {tool_name}')
        
        # Try to get display name from various possible attributes
        display_name = (
            getattr(tool, 'display_name', None) or
            getattr(tool, 'title', None) or
            tool_name.replace('_', ' ').replace('-', ' ').title()
        )
    else:
        # It's a dictionary
        tool_name = tool.get('name', '') or tool.get('id', '')
        tool_description = tool.get('description', f'Tool: {tool_name}')
        display_name = tool.get('display_name', tool_name.replace('_', ' ').replace('-', ' ').title())
    
    # Generate tags from the tool name
    tags = []
    if tool_name:
        # Split by underscores, hyphens, or camelCase
        import re
        parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', tool_name.replace('_', ' ').replace('-', ' '))
        tags = [part.lower() for part in parts if len(part) > 2]
    
    # Add additional tags based on common keywords in description
    keywords = ['create', 'update', 'delete', 'list', 'get', 'add', 'remove', 'edit', 'episode', 'part', 'item', 'block']
    for keyword in keywords:
        if keyword in tool_description.lower() and keyword not in tags:
            tags.append(keyword)
    
    # Generate examples based on the tool name and description
    examples = []
    if display_name:
        examples.append(f"{display_name.lower()}")
    if tool_description and len(tool_description) > 10:
        # Create a short example from the description
        desc_words = tool_description.lower().split()[:8]
        examples.append(' '.join(desc_words))
    
    return AgentSkill(
        id=tool_name,
        name=display_name,
        description=tool_description,
        tags=tags[:5],  # Limit to 5 tags
        examples=examples[:2],  # Limit to 2 examples
    )


async def get_mcp_tools(mcp_toolset) -> List:
    """
    Retrieve tools from an MCP toolset.
    
    Args:
        mcp_toolset: The MCP toolset instance
        
    Returns:
        List of tool definitions (MCPTool objects)
    """
    tools = []
    
    try:
        # Use get_tools method which we know works
        if hasattr(mcp_toolset, 'get_tools') and callable(mcp_toolset.get_tools):
            tools = await mcp_toolset.get_tools()
            logger.info(f"Retrieved {len(tools)} tools from get_tools() method")
            
    except Exception as e:
        logger.error(f"Error retrieving tools from MCP server: {e}")
    
    return tools


async def get_skills_from_mcp(mcp_toolset) -> List[AgentSkill]:
    """
    Retrieve skills from an MCP toolset.
    
    Args:
        mcp_toolset: The MCP toolset instance
        
    Returns:
        List of AgentSkill objects
    """
    skills = []
    
    try:
        # Get tools from the MCP server
        tools = await get_mcp_tools(mcp_toolset)
        
        if not tools:
            logger.warning("No tools retrieved from MCP server")
            return skills
        
        # Convert tools to skills
        for tool in tools:
            try:
                skill = tool_to_skill(tool)
                skills.append(skill)
                logger.debug(f"Created skill: {skill.id} - {skill.name}")
            except Exception as e:
                logger.error(f"Error converting tool to skill: {e}, tool: {tool}")
        
        logger.info(f"Successfully created {len(skills)} skills from MCP tools")
        
    except Exception as e:
        logger.error(f"Error in get_skills_from_mcp: {e}")
    
    return skills


def get_default_skills() -> List[AgentSkill]:
    """
    Get default skills as a fallback when MCP tools cannot be retrieved.
    
    Returns:
        List of default AgentSkill objects
    """
    return [
        AgentSkill(
            id="cuez_rundown_management",
            name="Cuez Rundown Management",
            description="Comprehensive tools for managing Cuez rundowns, episodes, parts, items, and blocks",
            tags=["cuez", "rundown", "episode", "management", "edit"],
            examples=["manage rundown", "edit episodes"],
        )
    ]
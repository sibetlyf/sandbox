from typing import AsyncGenerator, List
import pixabay
from pydantic import BaseModel, Field

class resource_format(BaseModel):
    id: str = Field(..., description="素材id")
    type: str = Field(..., description="素材类型")
    tags: str = Field(..., description="素材标签")
    url: str = Field(..., description="素材url")
    width: int = Field(..., description="素材宽度")
    height: int = Field(..., description="素材高度")


# @tool(name="pixabay search", description="search image and video from pixabay")
async def pixabay_search(query: str, 
                         key: str="53312803-19c141bade8d0b8e930a236ca", 
                         resource_type: str="image", 
                         resource_limit: int=10
                        ) -> AsyncGenerator[List[resource_format], None]:
    """
    search image and video from pixabay

    param key: str, the pixabay API key
    param resource_type: str, the type of resource to search, image or video
    
    return: list[dict], the search result
    """

    # 初始化搜索API
    px = pixabay.core(key)
    result_dict = []
    
    
    if resource_type == "image":
        search_result = px.query(query)
        # 只取前10个结果
        for _, image in enumerate(search_result.cache[:resource_limit]):
            img_id, img_type, tag, url, w, h = map(image.get, ("id", "type", "tags", "largeImageURL", "imageWidth", "imageHeight"))
            result_dict.append(resource_format(
                id=str(img_id),
                type=img_type,
                tags=tag,
                url=url,
                width=w,
                height=h,
            ))
        
    elif resource_type == "video":
        search_result = px.queryVideo(query)
         # 只取前10个结果
        for _, video in enumerate(search_result.cache[:10]):
            video_id, video_type, tag = map(video.get, ("id", "type", "tags"))
            url, w, h = map(video.get('videos').get('large').get, ("url", "width", "height"))
            result_dict.append(resource_format(
                id=str(video_id),
                type=video_type,
                tags=tag,
                url=url,
                width=w,
                height=h,
            ))
    yield result_dict
    




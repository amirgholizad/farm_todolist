from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from pydantic import BaseModel

from uuid import uuid4

class ListSummary(BaseModel):
    id: str
    name: str
    item_count: int


    @staticmethod
    def from_doc(doc) -> "ListSummary":
        return ListSummary(
            id=str(doc["_id"]),
            name=doc["name"],
            item_count=doc["item_count"]
        )
class ToDoListItem(BaseModel):
    id: str
    label: str
    completed: bool

    @staticmethod
    def from_doc(item) -> "ToDoListItem":
        return ToDoListItem(
            id=item["id"],
            label=item["label"],
            completed=item["completed"]
        )

class ToDoList(BaseModel):
    id: str
    name: str
    items: list[ToDoListItem]

    @staticmethod
    def from_doc(doc) -> "ToDoList":
        return ToDoList(
            id=str(doc["_id"]),
            name=doc["name"],
            items=[ToDoListItem.from_doc(item) for item in doc["items"]]
        )

class ToDoDAL:
    def __init__(self, todo_collection: AsyncIOMotorCollection):
        self._todo_collection = todo_collection

    async def list_todo_lists(self, session=None):
        async for doc in self._todo_collection.find(
            {},
            projection={"name": 1, "item_count": {"$size": "$items"}},
            sort={"name": 1},
            session=session,
            ):
            yield ListSummary.from_doc(doc)
    
    async def create_todo_list(self, name: str, session=None) -> str:
        result = await self._todo_collection.insert_one(
            {"name": name, "items": []},
            session=session,
        )
        return str(result.inserted_id)
    
    async def get_todo_list(self, id: str | ObjectID, session=None) -> ToDoList:
        doc = await self._todo_collection.find_one(
            {"_id": ObjectId(id)},
            session=session,
        )
        return ToDoList.from_doc(doc)
    
    async def delete_todo_list(self, id: str | ObjectID, session=None) -> bool:
        response = await self._todo_collection.delete_one(
            {"_id": ObjectId(id)},
            session=session,
        )
        return response.deleted_count == 1
    
    async def create_item(self, id: str | ObjectID, label: str, session=None) -> ToDoList | None:
        result = await self._todo_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$push": {"items": {"id": uuid4().hex, "label": label, "completed": False}}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if result:
            return ToDoList.from_doc(result)
        
    async def set_completed(self, doc_id: str | ObjectID, item_id: str, completed: bool, session=None) -> ToDoList | None:
        result = await self._todo_collection.find_one_and_update(
            {"_id": ObjectId(doc_id), "items.id": item_id},
            {"$set": {"items.$.completed": completed}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if result:
            return ToDoList.from_doc(result)
        
    async def delete_item(self, doc_id: str | ObjectID, item_id: str, session=None) -> ToDoList | None:
        result = await self._todo_collection.find_one_and_update(
            {"_id": ObjectId(doc_id)},
            {"$pull": {"items": {"id": item_id}}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if result:
            return ToDoList.from_doc(result)

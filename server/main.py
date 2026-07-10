from typing import Dict, List, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import api_messages
from attachments.base import BaseAttachments
from attachments.models import AttachmentCreateResponse
from auth.base import BaseAuth
from auth.models import CurrentUser, Login, Token
from global_config import AuthType, GlobalConfig, GlobalConfigResponseModel
from helpers import replace_base_href
from notes.base import BaseNotes
from notes.models import Note, NoteCreate, NoteUpdate, SearchResult

global_config = GlobalConfig()
auth: BaseAuth = global_config.load_auth()
note_storage_cache: Dict[str, BaseNotes] = {}
attachment_storage_cache: Dict[str, BaseAttachments] = {}
router = APIRouter()
app = FastAPI(
    docs_url=global_config.path_prefix + "/docs",
    openapi_url=global_config.path_prefix + "/openapi.json",
)
replace_base_href("client/dist/index.html", global_config.path_prefix)


if auth:

    def get_current_user(
        current_user: CurrentUser = Depends(auth.authenticate),
    ) -> CurrentUser:
        return current_user


else:

    def get_current_user() -> CurrentUser:
        return CurrentUser(
            username="anonymous",
            workspace_path=global_config.storage_path,
            is_admin=True,
            read_only=global_config.auth_type == AuthType.READ_ONLY,
        )


def require_modify(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.read_only:
        raise HTTPException(status_code=403, detail="User is read only.")
    return current_user


def get_note_storage(
    current_user: CurrentUser = Depends(get_current_user),
) -> BaseNotes:
    workspace_path = current_user.workspace_path
    if workspace_path not in note_storage_cache:
        note_storage_cache[workspace_path] = global_config.load_note_storage(
            workspace_path
        )
    return note_storage_cache[workspace_path]


def get_attachment_storage(
    current_user: CurrentUser = Depends(get_current_user),
) -> BaseAttachments:
    workspace_path = current_user.workspace_path
    if workspace_path not in attachment_storage_cache:
        attachment_storage_cache[workspace_path] = (
            global_config.load_attachment_storage(workspace_path)
        )
    return attachment_storage_cache[workspace_path]


def get_optional_current_user(request: Request) -> CurrentUser | None:
    if auth:
        return auth.authenticate_optional(request)
    return get_current_user()


# region UI
@router.get("/", include_in_schema=False)
@router.get("/login", include_in_schema=False)
@router.get("/search", include_in_schema=False)
@router.get("/new", include_in_schema=False)
@router.get("/note/{title}", include_in_schema=False)
def root(title: str = ""):
    with open("client/dist/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


# endregion


# region Auth
if global_config.auth_type not in [AuthType.NONE, AuthType.READ_ONLY]:

    @router.post("/api/token", response_model=Token)
    def token(data: Login):
        try:
            return auth.login(data)
        except ValueError:
            raise HTTPException(
                status_code=401, detail=api_messages.login_failed
            )


@router.get("/api/auth-check")
def auth_check(
    current_user: CurrentUser = Depends(get_current_user),
) -> str:
    """A lightweight endpoint that simply returns 'OK' if the user is
    authenticated."""
    return "OK"


# endregion


# region Notes
# Get Note
@router.get(
    "/api/notes/{title}",
    response_model=Note,
)
def get_note(
    title: str,
    note_storage: BaseNotes = Depends(get_note_storage),
):
    """Get a specific note."""
    try:
        return note_storage.get(title)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=api_messages.invalid_note_title
        )
    except FileNotFoundError:
        raise HTTPException(404, api_messages.note_not_found)


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Note
    @router.post(
        "/api/notes",
        response_model=Note,
    )
    def post_note(
        note: NoteCreate,
        current_user: CurrentUser = Depends(require_modify),
        note_storage: BaseNotes = Depends(get_note_storage),
    ):
        """Create a new note."""
        try:
            return note_storage.create(note)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )

    # Update Note
    @router.patch(
        "/api/notes/{title}",
        response_model=Note,
    )
    def patch_note(
        title: str,
        data: NoteUpdate,
        current_user: CurrentUser = Depends(require_modify),
        note_storage: BaseNotes = Depends(get_note_storage),
    ):
        try:
            return note_storage.update(title, data)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)

    # Delete Note
    @router.delete(
        "/api/notes/{title}",
        response_model=None,
    )
    def delete_note(
        title: str,
        current_user: CurrentUser = Depends(require_modify),
        note_storage: BaseNotes = Depends(get_note_storage),
    ):
        try:
            note_storage.delete(title)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)


# endregion


# region Search
@router.get(
    "/api/search",
    response_model=List[SearchResult],
)
def search(
    term: str,
    sort: Literal["score", "title", "lastModified"] = "score",
    order: Literal["asc", "desc"] = "desc",
    limit: int = None,
    note_storage: BaseNotes = Depends(get_note_storage),
):
    """Perform a full text search on all notes."""
    if sort == "lastModified":
        sort = "last_modified"
    return note_storage.search(term, sort=sort, order=order, limit=limit)


@router.get(
    "/api/tags",
    response_model=List[str],
)
def get_tags(note_storage: BaseNotes = Depends(get_note_storage)):
    """Get a list of all indexed tags."""
    return note_storage.get_tags()


# endregion


# region Config
@router.get("/api/config", response_model=GlobalConfigResponseModel)
def get_config(request: Request):
    """Retrieve server-side config required for the UI."""
    current_user = get_optional_current_user(request)
    return GlobalConfigResponseModel(
        auth_type=global_config.auth_type,
        quick_access_hide=global_config.quick_access_hide,
        quick_access_title=global_config.quick_access_title,
        quick_access_term=global_config.quick_access_term,
        quick_access_sort=global_config.quick_access_sort,
        quick_access_limit=global_config.quick_access_limit,
        username=current_user.username if current_user else None,
        is_admin=current_user.is_admin if current_user else False,
        can_modify=current_user.read_only is False if current_user else False,
    )


# endregion


# region Attachments
# Get Attachment
@router.get(
    "/api/attachments/{filename}",
)
# Include a secondary route used to create relative URLs that can be used
# outside the context of flatnotes (e.g. "/attachments/image.jpg").
@router.get(
    "/attachments/{filename}",
    include_in_schema=False,
)
def get_attachment(
    filename: str,
    attachment_storage: BaseAttachments = Depends(get_attachment_storage),
):
    """Download an attachment."""
    try:
        return attachment_storage.get(filename)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=api_messages.invalid_attachment_filename,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=api_messages.attachment_not_found
        )


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Attachment
    @router.post(
        "/api/attachments",
        response_model=AttachmentCreateResponse,
    )
    def post_attachment(
        file: UploadFile,
        current_user: CurrentUser = Depends(require_modify),
        attachment_storage: BaseAttachments = Depends(get_attachment_storage),
    ):
        """Upload an attachment."""
        try:
            return attachment_storage.create(file)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_attachment_filename,
            )
        except FileExistsError:
            raise HTTPException(409, api_messages.attachment_exists)


# endregion


# region Healthcheck
@router.get("/health")
def healthcheck() -> str:
    """A lightweight endpoint that simply returns 'OK' to indicate the server
    is running."""
    return "OK"


# endregion

app.include_router(router, prefix=global_config.path_prefix)
app.mount(
    global_config.path_prefix,
    StaticFiles(directory="client/dist"),
    name="dist",
)

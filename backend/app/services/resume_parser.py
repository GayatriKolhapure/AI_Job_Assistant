"""Resume parser service supporting PyMuPDF for PDF and python-docx for DOCX with deterministic and LLM extraction."""

import io
import json
import logging
import os
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import pymupdf  # PyMuPDF
import docx

from backend.app.core.config import get_settings
from backend.app.schemas.resume import (
    EducationDetail,
    ExperienceDetail,
    ProjectDetail,
    ResumeProfile,
    ResumeParseResponse,
)

logger = logging.getLogger("uvicorn.error")

# Broad taxonomy of technical and domain skills for deterministic recognition
TECH_SKILLS_ONTOLOGY = {
    # Programming Languages
    "python", "java", "c", "c++", "c#", "javascript", "typescript", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "sql", "bash", "shell",
    # Frameworks & Libraries
    "spring", "spring boot", "react", "react.js", "reactjs", "angular", "vue", "vue.js",
    "node.js", "nodejs", "express", "express.js", "django", "flask", "fastapi", "next.js",
    "nest.js", "dotnet", ".net", "asp.net", "hibernate", "jpa", "redux", "tailwind",
    "bootstrap", "jquery", "graphql", "rest", "rest api", "microservices",
    # Databases & Caches
    "mysql", "postgresql", "postgres", "sqlite", "mongodb", "redis", "oracle", "mariadb",
    "cassandra", "dynamodb", "elasticsearch", "neo4j", "firebase",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "ci/cd", "jenkins", "github actions", "gitlab", "linux", "nginx", "apache",
    # AI & Data Science
    "machine learning", "deep learning", "ai", "nlp", "computer vision", "tensorflow",
    "pytorch", "scikit-learn", "pandas", "numpy", "opencv", "langchain", "langgraph",
    "openai", "llm", "rag", "huggingface",
    # Core CS & Tools
    "git", "github", "gitlab", "jira", "postman", "agile", "scrum", "oop",
    "data structures", "algorithms", "system design", "unit testing", "junit", "pytest",
}

DESIGNATION_KEYWORDS = [
    "software engineer", "software developer", "sde", "full stack developer", "full stack engineer",
    "frontend developer", "frontend engineer", "backend developer", "backend engineer",
    "java developer", "python developer", "react developer", "node developer",
    "devops engineer", "cloud engineer", "cloud architect", "site reliability engineer",
    "data scientist", "data engineer", "data analyst", "machine learning engineer", "ai engineer",
    "cyber security analyst", "security engineer", "qa engineer", "quality assurance",
    "database administrator", "dba", "systems engineer", "intern", "sde intern", "fresher"
]


class ResumeParsingError(Exception):
    """Base exception for resume parsing errors."""

    def __init__(self, message: str, error_code: str = "UNREADABLE_RESUME", status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class UnsupportedFormatError(ResumeParsingError):
    def __init__(self, message: str = "Unsupported file format. Please upload your resume in PDF or DOCX format."):
        super().__init__(message, error_code="UNSUPPORTED_FORMAT", status_code=415)


class EmptyFileError(ResumeParsingError):
    def __init__(self, message: str = "Your uploaded file is empty. Please upload a valid resume."):
        super().__init__(message, error_code="EMPTY_FILE", status_code=400)


class FileTooLargeError(ResumeParsingError):
    def __init__(self, message: str = "File exceeds maximum allowed size of 5 MB. Please upload a smaller file."):
        super().__init__(message, error_code="FILE_TOO_LARGE", status_code=413)


class CorruptedFileError(ResumeParsingError):
    def __init__(self, message: str = "I couldn't read your resume. The file may be corrupted. Please upload another copy."):
        super().__init__(message, error_code="CORRUPTED_FILE", status_code=422)


class UnreadableResumeError(ResumeParsingError):
    def __init__(self, message: str = "I couldn't extract readable text from your resume. Please upload a clear, text-based PDF or DOCX file."):
        super().__init__(message, error_code="UNREADABLE_RESUME", status_code=422)


def validate_file_content(file_bytes: bytes, filename: str) -> None:
    """Validate file content, headers, and magic bytes before parsing."""
    settings = get_settings()
    fn_lower = filename.lower().strip()

    # 1. Filename extension check
    if not (fn_lower.endswith(".pdf") or fn_lower.endswith(".docx")):
        raise UnsupportedFormatError("Unsupported file format. Please upload your resume in PDF or DOCX format.")

    # 2. Check empty file (0 bytes)
    if len(file_bytes) == 0:
        raise EmptyFileError("Your uploaded file is empty. Please upload a valid resume.")

    # 3. Check maximum file size (5 MB)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise FileTooLargeError(f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB. Please upload a smaller file.")

    # 4. Content signature / magic byte inspection
    image_prefixes = [
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"GIF87a",
        b"GIF89a",
        b"BM",
        b"RIFF",
    ]
    for prefix in image_prefixes:
        if file_bytes.startswith(prefix):
            raise UnsupportedFormatError("Unsupported file format. Please upload your resume in PDF or DOCX format.")

    if fn_lower.endswith(".pdf"):
        # PDF specification requires %PDF- within the first 1024 bytes
        if b"%PDF-" not in file_bytes[:1024]:
            # Detect whether it is plain text or corrupted binary
            try:
                file_bytes[:512].decode("utf-8")
                raise UnsupportedFormatError("Unsupported file format. Please upload your resume in PDF or DOCX format.")
            except UnicodeDecodeError:
                raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")

    elif fn_lower.endswith(".docx"):
        # DOCX is an Open Packaging Conventions ZIP package
        zip_signatures = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
        if not any(file_bytes.startswith(sig) for sig in zip_signatures):
            try:
                file_bytes[:512].decode("utf-8")
                raise UnsupportedFormatError("Unsupported file format. Please upload your resume in PDF or DOCX format.")
            except UnicodeDecodeError:
                raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")

        # Verify valid zip file
        if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
            raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")

        # Verify word document structure
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                names = zf.namelist()
                if not any("document.xml" in n or "[Content_Types].xml" in n for n in names):
                    raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")
        except Exception:
            raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF bytes using PyMuPDF."""
    text_parts = []
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        logger.warning(f"PyMuPDF failed to open PDF document: {e}")
        raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")

    try:
        if doc.page_count == 0:
            raise UnreadableResumeError("I couldn't extract readable text from your resume. Please upload a clear, text-based PDF or DOCX file.")

        for page in doc:
            t = page.get_text("text")
            if t:
                text_parts.append(t)
    except ResumeParsingError:
        raise
    except Exception as e:
        logger.warning(f"PyMuPDF failed while extracting text from pages: {e}")
        raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")
    finally:
        try:
            doc.close()
        except Exception:
            pass

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise UnreadableResumeError("I couldn't extract readable text from your resume. Please upload a clear, text-based PDF or DOCX file.")

    # Detect resumes containing only blank spaces or special characters
    clean_alphanumeric = re.sub(r"[\W_]+", "", full_text)
    if len(clean_alphanumeric) < 20:
        raise UnreadableResumeError("I couldn't extract readable text from your resume. Please upload a clear, text-based PDF or DOCX file.")

    return full_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract clean text from DOCX bytes using python-docx."""
    if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
        raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text.strip())
        full_text = "\n".join(paragraphs).strip()
    except Exception as e:
        logger.warning(f"python-docx failed to read DOCX: {e}")
        raise CorruptedFileError("I couldn't read your resume. The file may be corrupted. Please upload another copy.")

    if not full_text:
        raise UnreadableResumeError("I couldn't extract readable text from your resume. Please upload a clear, text-based PDF or DOCX file.")

    clean_alphanumeric = re.sub(r"[\W_]+", "", full_text)
    if len(clean_alphanumeric) < 20:
        raise UnreadableResumeError("I couldn't extract readable text from your resume. Please upload a clear, text-based PDF or DOCX file.")

    return full_text


class ResumeParserService:
    """High-accuracy resume extraction service using pattern recognition and optional LLM structuring."""

    @staticmethod
    def extract_email(text: str) -> str:
        """Extract primary email address."""
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
        matches = re.findall(pattern, text)
        return matches[0].strip() if matches else ""

    @staticmethod
    def extract_phone(text: str) -> str:
        """Extract primary telephone number."""
        patterns = [
            r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
            r"(\+91[-\s]?)?[6-9]\d{9}",  # Common Indian phone pattern
        ]
        for p in patterns:
            matches = re.findall(p, text)
            if matches:
                found = re.search(r"(\+?\d[\d\s-]{8,15}\d)", text)
                if found:
                    cleaned = re.sub(r"[^\d+]", "", found.group(0))
                    if 10 <= len(cleaned.replace("+", "")) <= 13:
                        return found.group(0).strip()
        return ""

    @staticmethod
    def extract_name(text: str) -> str:
        """Heuristic name extraction from top resume lines."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            if "@" in line or "http" in line or "resume" in line.lower() or "curriculum" in line.lower():
                continue
            words = line.split()
            if 1 <= len(words) <= 4 and all(w.isalpha() for w in words):
                return line
        return ""

    @staticmethod
    def extract_designation(text: str) -> str:
        """Identify candidate primary designation or target role."""
        text_lower = text.lower()
        for desig in DESIGNATION_KEYWORDS:
            pattern = r"\b" + re.escape(desig) + r"\b"
            if re.search(pattern, text_lower):
                return desig.title()
        return "Software Developer"

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Recognize and normalize technical skills from ontology."""
        text_lower = text.lower()
        found_skills = set()

        for skill in TECH_SKILLS_ONTOLOGY:
            escaped = re.escape(skill)
            if re.search(r"(?:^|[^a-zA-Z0-9_#+])" + escaped + r"(?:$|[^a-zA-Z0-9_#+])", text_lower):
                found_skills.add(ResumeParserService.canonicalize_skill(skill))

        priority = ["Python", "Java", "React", "Spring Boot", "FastAPI", "SQL", "Docker", "Node.js"]
        sorted_skills = sorted(
            list(found_skills),
            key=lambda s: (0 if s in priority else 1, s)
        )
        return sorted_skills

    @staticmethod
    def canonicalize_skill(skill: str) -> str:
        """Normalize skill display formatting."""
        title_map = {
            "c++": "C++",
            "c#": "C#",
            "ci/cd": "CI/CD",
            "spring boot": "Spring Boot",
            "react.js": "React",
            "reactjs": "React",
            "vue.js": "Vue",
            "vue": "Vue",
            "next.js": "Next.js",
            "mysql": "MySQL",
            "postgresql": "PostgreSQL",
            "mongodb": "MongoDB",
            "fastapi": "FastAPI",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "git": "Git",
            "github": "GitHub",
            "postman": "Postman",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "python": "Python",
            "java": "Java",
            "html": "HTML",
            "css": "CSS",
        }
        return title_map.get(skill.lower(), skill.title())

    @staticmethod
    def extract_experience_years(text: str) -> float:
        """Estimate experience in years from years mentioned or date ranges."""
        text_lower = text.lower()

        if "fresher" in text_lower or "entry level" in text_lower or "intern" in text_lower:
            exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?\s*(?:of)?\s*experience", text_lower)
            if exp_match:
                try:
                    return float(exp_match.group(1))
                except ValueError:
                    pass
            return 0.0

        exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?\s*(?:of)?\s*experience", text_lower)
        if exp_match:
            try:
                return float(exp_match.group(1))
            except ValueError:
                pass

        year_matches = re.findall(r"\b(20[0-2][0-9])\b", text)
        if len(year_matches) >= 2:
            years = [int(y) for y in year_matches]
            min_y = min(years)
            max_y = max(years)
            span = max_y - min_y
            if 0 < span <= 15:
                return float(span)

        return 0.0

    @classmethod
    def parse_deterministic(cls, text: str) -> ResumeProfile:
        """Deterministic parsing relying on tokenizers, regex, and section splitting."""
        name = cls.extract_name(text)
        email = cls.extract_email(text)
        phone = cls.extract_phone(text)
        designation = cls.extract_designation(text)
        skills = cls.extract_skills(text)
        exp_years = cls.extract_experience_years(text)

        education = []
        edu_keywords = ["b.tech", "btech", "b.e", "bachelor", "m.tech", "master", "mca", "bca", "bsc", "b.sc", "computer science"]
        text_lower = text.lower()
        for kw in edu_keywords:
            if kw in text_lower:
                education.append(EducationDetail(
                    institution="University / Institute",
                    degree=kw.upper(),
                    field_of_study="Computer Science & Engineering",
                    year="Completed"
                ))
                break

        projects = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line_s = line.strip()
            if "project" in line_s.lower() and len(line_s) < 50:
                desc = " ".join([l.strip() for l in lines[i+1:i+4] if l.strip()])
                if desc:
                    projects.append(ProjectDetail(
                        title=line_s,
                        description=desc[:200],
                        technologies=cls.extract_skills(desc)
                    ))
                if len(projects) >= 3:
                    break

        return ResumeProfile(
            name=name or "Candidate",
            email=email,
            phone=phone,
            designation=designation,
            skills=skills,
            experience_years=exp_years,
            experience_details=[],
            education=education,
            projects=projects,
            certifications=[],
        )

    @classmethod
    async def parse_with_llm(cls, text: str) -> Optional[ResumeProfile]:
        """Optionally use OpenAI structured completion to extract high-fidelity resume profile."""
        settings = get_settings()
        if settings.is_mock_mode:
            return None

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
                timeout=float(settings.llm_timeout_seconds),
            )

            prompt = (
                "You are an expert resume parsing engine. Analyze the following resume text and extract "
                "structured information strictly in JSON format matching this schema:\n"
                "{\n"
                "  \"name\": string,\n"
                "  \"email\": string,\n"
                "  \"phone\": string,\n"
                "  \"designation\": string,\n"
                "  \"skills\": [string],\n"
                "  \"experience_years\": number,\n"
                "  \"education\": [{\"institution\": str, \"degree\": str, \"field_of_study\": str, \"year\": str}],\n"
                "  \"projects\": [{\"title\": str, \"description\": str, \"technologies\": [str]}],\n"
                "  \"certifications\": [string]\n"
                "}\n"
                "Do NOT invent details. If a field is missing, use empty strings or empty arrays.\n\n"
                f"RESUME TEXT:\n{text[:4000]}"
            )

            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You extract structured resume JSON. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            content = response.choices[0].message.content
            if content:
                data = json.loads(content)
                return ResumeProfile(**data)
        except Exception as e:
            logger.warning(f"LLM resume parsing failed, falling back to deterministic parser: {e}")

        return None

    @classmethod
    async def parse_file(cls, file_bytes: bytes, filename: str) -> ResumeParseResponse:
        """Parse uploaded resume document (PDF or DOCX) into validated ResumeProfile."""
        # Validate content, extension, size, and headers
        validate_file_content(file_bytes, filename)

        fn_lower = filename.lower()
        if fn_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_bytes)
        elif fn_lower.endswith(".docx"):
            raw_text = extract_text_from_docx(file_bytes)
        else:
            raise UnsupportedFormatError(
                "Unsupported file format. Please upload your resume in PDF or DOCX format."
            )

        # Attempt LLM structured parsing first if live key available
        profile = await cls.parse_with_llm(raw_text)
        parse_method = "llm"

        if profile is None:
            profile = cls.parse_deterministic(raw_text)
            parse_method = "deterministic"

        preview = raw_text[:300].strip().replace("\n", " ")
        if len(raw_text) > 300:
            preview += "..."

        return ResumeParseResponse(
            success=True,
            filename=filename,
            profile=profile,
            parse_method=parse_method,
            text_preview=preview,
            message="Resume parsed successfully.",
        )

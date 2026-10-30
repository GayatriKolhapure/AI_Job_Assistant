"""Resume parser service supporting PyMuPDF for PDF and python-docx for DOCX with deterministic and LLM extraction."""

import io
import json
import logging
import os
import re
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
    """Raised when resume extraction fails due to format or content issues."""
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF bytes using PyMuPDF."""
    text_parts = []
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            t = page.get_text("text")
            if t:
                text_parts.append(t)
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF failed to read PDF: {e}")
        raise ResumeParsingError(f"Unable to read PDF file: {str(e)}")

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ResumeParsingError("PDF file contains no extractable text (it may be scanned or empty).")
    return full_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract clean text from DOCX bytes using python-docx."""
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
        logger.error(f"python-docx failed to read DOCX: {e}")
        raise ResumeParsingError(f"Unable to read DOCX file: {str(e)}")

    if not full_text:
        raise ResumeParsingError("DOCX file contains no extractable text.")
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
                # Find full string match in context
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
            # Skip if contains email or url or keywords
            if "@" in line or "http" in line or "resume" in line.lower() or "curriculum" in line.lower():
                continue
            # Candidate names are typically 2-4 words, capitalized
            words = line.split()
            if 1 <= len(words) <= 4 and all(w.isalpha() for w in words):
                return line
        return ""

    @staticmethod
    def extract_designation(text: str) -> str:
        """Identify candidate primary designation or target role."""
        text_lower = text.lower()
        for kw in DESIGNATION_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                return kw.title()
        return "Software Engineer"

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """Extract technical skills matching known ontology with word boundaries."""
        text_lower = text.lower()
        found_skills = set()
        for skill in TECH_SKILLS_ONTOLOGY:
            # Handle special symbols like C++, C#, .NET
            if "+" in skill or "#" in skill or "." in skill:
                escaped = re.escape(skill)
                if re.search(rf"(?:^|\s|[,;/]){escaped}(?:$|\s|[,;/])", text_lower):
                    found_skills.add(cls._format_skill_name(skill))
            else:
                if re.search(rf"\b{re.escape(skill)}\b", text_lower):
                    found_skills.add(cls._format_skill_name(skill))
        return sorted(list(found_skills))

    @staticmethod
    def _format_skill_name(skill: str) -> str:
        """Canonical casing for common skills."""
        title_map = {
            "c++": "C++",
            "c#": "C#",
            ".net": ".NET",
            "asp.net": "ASP.NET",
            "sql": "SQL",
            "aws": "AWS",
            "gcp": "GCP",
            "ci/cd": "CI/CD",
            "ai": "AI",
            "ml": "ML",
            "nlp": "NLP",
            "llm": "LLM",
            "rag": "RAG",
            "rest api": "REST API",
            "rest": "REST API",
            "spring boot": "Spring Boot",
            "node.js": "Node.js",
            "nodejs": "Node.js",
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

        # Check for explicit "fresher" or "student" or "entry level"
        if "fresher" in text_lower or "entry level" in text_lower or "intern" in text_lower:
            # Check if there is explicit experience stated
            exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?\s*(?:of)?\s*experience", text_lower)
            if exp_match:
                try:
                    return float(exp_match.group(1))
                except ValueError:
                    pass
            return 0.0

        # Pattern: "X years of experience" or "X+ yrs experience"
        exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?\s*(?:of)?\s*experience", text_lower)
        if exp_match:
            try:
                return float(exp_match.group(1))
            except ValueError:
                pass

        # Pattern: Count year intervals (e.g. 2021 - 2024)
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

        # Detect education keywords
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

        # Detect projects from text
        projects = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line_s = line.strip()
            if "project" in line_s.lower() and len(line_s) < 50:
                # Next few lines might be project content
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
        fn_lower = filename.lower()
        if fn_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_bytes)
        elif fn_lower.endswith(".docx") or fn_lower.endswith(".doc"):
            raw_text = extract_text_from_docx(file_bytes)
        else:
            raise ResumeParsingError(
                f"Unsupported file type for '{filename}'. Only PDF (.pdf) and Word (.docx) files are supported."
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

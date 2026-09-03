"""Application-logic layer.

Every interface - CLI, FastAPI, exports, the mission solver - goes through these
services, so a motor built by the inverse solver and one built by hand are the same
object and there is never a second code path for the same job (Section 4).
"""

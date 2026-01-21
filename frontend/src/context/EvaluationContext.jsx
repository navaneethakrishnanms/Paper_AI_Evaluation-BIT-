/**
 * Evaluation Context - Global state management for the exam evaluation system.
 * Manages files, job queue, and evaluation results.
 */
import React, { createContext, useContext, useReducer, useCallback } from 'react';

// Initial state
const initialState = {
    // Mode selection
    examMode: 'PT-2', // PT-1 (disabled), PT-2 (default)

    // Master files (uploaded once, reused for all students)
    masterFiles: {
        questionPaper: null,
        answerKey: null,
    },

    // Student files queue (max 40)
    studentFiles: [],

    // Job queue with status tracking
    jobs: [], // { id, filename, jobId, status, stage, result, error }

    // Current processing state
    isProcessing: false,
    currentJobIndex: -1,

    // UI state
    selectedJobId: null, // For result modal
};

// Action types
const ACTIONS = {
    SET_MODE: 'SET_MODE',
    SET_MASTER_FILE: 'SET_MASTER_FILE',
    ADD_STUDENT_FILES: 'ADD_STUDENT_FILES',
    REMOVE_STUDENT_FILE: 'REMOVE_STUDENT_FILE',
    CLEAR_ALL: 'CLEAR_ALL',
    START_PROCESSING: 'START_PROCESSING',
    UPDATE_JOB: 'UPDATE_JOB',
    SET_CURRENT_JOB: 'SET_CURRENT_JOB',
    STOP_PROCESSING: 'STOP_PROCESSING',
    SELECT_JOB: 'SELECT_JOB',
    RESET_JOBS: 'RESET_JOBS',
};

// Reducer
function evaluationReducer(state, action) {
    switch (action.type) {
        case ACTIONS.SET_MODE:
            return { ...state, examMode: action.payload };

        case ACTIONS.SET_MASTER_FILE:
            return {
                ...state,
                masterFiles: {
                    ...state.masterFiles,
                    [action.payload.type]: action.payload.file,
                },
            };

        case ACTIONS.ADD_STUDENT_FILES: {
            const newFiles = action.payload.filter(
                file => !state.studentFiles.some(f => f.name === file.name)
            );
            const combined = [...state.studentFiles, ...newFiles].slice(0, 40);
            return { ...state, studentFiles: combined };
        }

        case ACTIONS.REMOVE_STUDENT_FILE:
            return {
                ...state,
                studentFiles: state.studentFiles.filter((_, i) => i !== action.payload),
                jobs: state.jobs.filter((_, i) => i !== action.payload),
            };

        case ACTIONS.CLEAR_ALL:
            return initialState;

        case ACTIONS.START_PROCESSING: {
            // Initialize jobs from student files
            const jobs = state.studentFiles.map((file, index) => ({
                id: index,
                filename: file.name,
                jobId: null,
                status: 'waiting', // waiting, uploading, ocr, evaluating, completed, failed
                stage: null,
                result: null,
                error: null,
            }));
            return { ...state, isProcessing: true, jobs, currentJobIndex: 0 };
        }

        case ACTIONS.UPDATE_JOB:
            return {
                ...state,
                jobs: state.jobs.map(job =>
                    job.id === action.payload.id
                        ? { ...job, ...action.payload.updates }
                        : job
                ),
            };

        case ACTIONS.SET_CURRENT_JOB:
            return { ...state, currentJobIndex: action.payload };

        case ACTIONS.STOP_PROCESSING:
            return { ...state, isProcessing: false, currentJobIndex: -1 };

        case ACTIONS.SELECT_JOB:
            return { ...state, selectedJobId: action.payload };

        case ACTIONS.RESET_JOBS:
            return { ...state, jobs: [], currentJobIndex: -1, isProcessing: false };

        default:
            return state;
    }
}

// Context
const EvaluationContext = createContext(null);

// Provider component
export function EvaluationProvider({ children }) {
    const [state, dispatch] = useReducer(evaluationReducer, initialState);

    // Actions
    const setMode = useCallback((mode) => {
        dispatch({ type: ACTIONS.SET_MODE, payload: mode });
    }, []);

    const setMasterFile = useCallback((type, file) => {
        dispatch({ type: ACTIONS.SET_MASTER_FILE, payload: { type, file } });
    }, []);

    const addStudentFiles = useCallback((files) => {
        dispatch({ type: ACTIONS.ADD_STUDENT_FILES, payload: Array.from(files) });
    }, []);

    const removeStudentFile = useCallback((index) => {
        dispatch({ type: ACTIONS.REMOVE_STUDENT_FILE, payload: index });
    }, []);

    const clearAll = useCallback(() => {
        dispatch({ type: ACTIONS.CLEAR_ALL });
    }, []);

    const startProcessing = useCallback(() => {
        dispatch({ type: ACTIONS.START_PROCESSING });
    }, []);

    const updateJob = useCallback((id, updates) => {
        dispatch({ type: ACTIONS.UPDATE_JOB, payload: { id, updates } });
    }, []);

    const setCurrentJob = useCallback((index) => {
        dispatch({ type: ACTIONS.SET_CURRENT_JOB, payload: index });
    }, []);

    const stopProcessing = useCallback(() => {
        dispatch({ type: ACTIONS.STOP_PROCESSING });
    }, []);

    const selectJob = useCallback((jobId) => {
        dispatch({ type: ACTIONS.SELECT_JOB, payload: jobId });
    }, []);

    const resetJobs = useCallback(() => {
        dispatch({ type: ACTIONS.RESET_JOBS });
    }, []);

    // Computed values
    const canStartEvaluation =
        state.masterFiles.questionPaper !== null &&
        state.masterFiles.answerKey !== null &&
        state.studentFiles.length > 0 &&
        !state.isProcessing;

    const completedCount = state.jobs.filter(j => j.status === 'completed').length;
    const failedCount = state.jobs.filter(j => j.status === 'failed').length;
    const totalCount = state.jobs.length;

    const value = {
        state,
        actions: {
            setMode,
            setMasterFile,
            addStudentFiles,
            removeStudentFile,
            clearAll,
            startProcessing,
            updateJob,
            setCurrentJob,
            stopProcessing,
            selectJob,
            resetJobs,
        },
        computed: {
            canStartEvaluation,
            completedCount,
            failedCount,
            totalCount,
        },
    };

    return (
        <EvaluationContext.Provider value={value}>
            {children}
        </EvaluationContext.Provider>
    );
}

// Hook
export function useEvaluation() {
    const context = useContext(EvaluationContext);
    if (!context) {
        throw new Error('useEvaluation must be used within EvaluationProvider');
    }
    return context;
}

/**
 * ModeSelector - Exam mode selection dropdown.
 * PT-1 is disabled (coming soon), PT-2 is enabled and default.
 */
import React from 'react';
import { useEvaluation } from '../context/EvaluationContext';

export default function ModeSelector({ disabled }) {
    const { state, actions } = useEvaluation();

    return (
        <div className="mode-selector">
            <label className="mode-label">Exam Mode</label>
            <select
                className="mode-dropdown"
                value={state.examMode}
                onChange={(e) => actions.setMode(e.target.value)}
                disabled={disabled}
            >
                <option value="PT-1" disabled>
                    Periodical Test 1 (PT-1) — Coming Soon
                </option>
                <option value="PT-2">
                    Periodical Test 2 (PT-2)
                </option>
            </select>
        </div>
    );
}

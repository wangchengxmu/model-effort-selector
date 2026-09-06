"""Offline task-to-model heuristics. Recommendations only; no inference or writes."""
import argparse
from dataclasses import dataclass
import json

from inspect_project import inspect_project

SNAPSHOT_DATE = '2026-09-06'
ASTRA, SOL, TERRA, LUNA = ('gpt-6-astra', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna')
SPARK = 'gpt-5.3-codex-spark'
BASE_EFFORTS = ('low', 'medium', 'high', 'xhigh')
# Example Codex host snapshot, not universal availability or API compatibility.
CATALOG = {
    ASTRA: BASE_EFFORTS + ('max', 'ultra'),
    SOL: BASE_EFFORTS + ('max', 'ultra'),
    TERRA: BASE_EFFORTS + ('max', 'ultra'),
    LUNA: BASE_EFFORTS + ('max',),
    'gpt-5.5': BASE_EFFORTS,
    'gpt-5.4-mini': BASE_EFFORTS,
    SPARK: BASE_EFFORTS,
}
WORKLOADS = ('extraction', 'writing', 'scientific-writing', 'coding', 'debugging', 'architecture', 'analysis', 'synthesis', 'admin')


@dataclass(frozen=True)
class Task:
    workload: str
    complexity: str = 'routine'
    priority: str = 'balanced'
    figures: bool = False
    results: bool = False
    calculations: bool = False
    critical: bool = False
    deep_reasoning: bool = False
    reasoning_blocked: bool = False
    evidence_missing: bool = False
    model: str | None = None
    effort: str | None = None


def recommend(task, available=None):
    if task.workload not in WORKLOADS or task.complexity not in ('routine', 'integrated', 'hard'):
        raise ValueError('Unknown workload or complexity')
    if task.priority not in ('economy', 'balanced', 'quality', 'speed'):
        raise ValueError('Unknown priority')
    permitted = set(CATALOG) if available is None else set(available)
    if not permitted or permitted - CATALOG.keys():
        raise ValueError('Empty or unknown availability list; refresh host metadata before recommending')
    model, effort = TERRA, 'medium'
    reason = 'Normal multi-step work with checkable outputs.'
    if task.workload == 'extraction' and task.complexity != 'hard':
        model = LUNA
        effort = 'low' if task.complexity == 'routine' else 'medium'
        reason = 'Start with a small model for routine extraction; validate it on your own examples.'
    elif task.complexity == 'routine' and task.workload in ('admin', 'coding', 'writing'):
        model, effort = LUNA, 'low'
        reason = 'Bounded work with direct acceptance checks.'
    elif task.workload == 'synthesis' and task.complexity == 'integrated':
        model, effort = SOL, 'high'
        reason = 'Substantial but scoped synthesis across several sources.'
    if task.workload == 'architecture':
        model, effort = ASTRA, 'medium'
        reason = 'Architectural judgment; start at medium for conventional, constrained design.'
    if task.figures or (task.workload == 'scientific-writing' and task.results):
        model, effort = ASTRA, 'medium'
        reason = 'Source-grounded scientific judgment; straightforward inspection does not require high.'
        if task.complexity != 'routine':
            effort = 'high'
            reason = 'Interpretation couples experimental evidence, figures, or derived conclusions.'
    if task.complexity == 'hard':
        model, effort = ASTRA, 'high'
        reason = 'The problem itself requires difficult reasoning, not just many steps.'
    if task.critical:
        model = ASTRA
        if effort == 'low':
            effort = 'medium'
        reason += ' Consequential outcomes justify stronger review, not automatic xhigh.'
    if task.deep_reasoning or task.reasoning_blocked:
        model, effort = ASTRA, ('high' if task.evidence_missing else 'xhigh')
        reason = ('Acquire missing evidence before escalating effort.' if task.evidence_missing else
                  'Inherently difficult reasoning or a specific unresolved issue after a checked high-effort pass.')
    if model in (LUNA, TERRA, SOL) and task.priority == 'quality' and task.workload != 'extraction':
        model = {LUNA: TERRA, TERRA: SOL, SOL: ASTRA}[model]
        if effort == 'low':
            effort = 'medium'
        reason += ' Capability preference raises the model tier without maximizing effort.'
    if task.workload == 'coding' and model == LUNA and task.priority == 'speed':
        model, effort = SPARK, 'medium'
        reason = 'Small known coding fix with immediate tests and latency priority.'
    warnings = []
    if task.evidence_missing:
        warnings.append('Evidence/tool repair comes first; no model can supply missing measurements or sources.')
    if task.calculations:
        warnings.append('Execute calculations with tools; preserve inputs, units, code, and outputs. Frequency alone does not raise effort.')
    if task.model:
        if task.model not in CATALOG or task.model not in permitted:
            raise ValueError('Explicit model is unknown or unavailable; do not substitute silently')
        model = task.model
        warnings.append('Explicit model preserved; verify that it can meet the task acceptance criteria.')
    if task.effort:
        effort = task.effort
        warnings.append('Explicit effort preserved; this is not an independently optimized effort recommendation.')
    if effort not in CATALOG[model]:
        raise ValueError(f'{model} does not support {effort} in the recorded host catalog')
    status = 'recommended' if model in permitted else 'recommended_pair_unavailable'
    if status != 'recommended':
        warnings.append('No automatic fallback: review the available models or split the task before choosing a weaker tier.')
    return {
        'status': status, 'model': model if status == 'recommended' else None,
        'reasoning_effort': effort if status == 'recommended' else None,
        'preferred_pair': {'model': model, 'effort': effort}, 'reason': reason,
        'warnings': warnings, 'catalog_snapshot': SNAPSHOT_DATE,
        'availability_basis': 'caller_supplied' if available is not None else 'unverified_snapshot',
        'available_models': sorted(permitted), 'dispatch_performed': False,
        'basis': 'Local heuristics, not a model benchmark or quota estimate',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workload', required=True, choices=WORKLOADS)
    parser.add_argument('--complexity', choices=('routine', 'integrated', 'hard'), default='routine')
    parser.add_argument('--priority', choices=('economy', 'balanced', 'quality', 'speed'), default='balanced')
    for flag in ('figures', 'results', 'calculations', 'critical', 'deep-reasoning', 'reasoning-blocked', 'evidence-missing'):
        parser.add_argument('--' + flag, action='store_true')
    parser.add_argument('--model', help='Preserve an explicitly requested model ID')
    parser.add_argument('--effort', help='Preserve explicitly requested effort, if supported')
    parser.add_argument('--available', help='Comma-separated IDs observed in current host metadata')
    parser.add_argument('--project', help='Project folder to inspect before a project-specific recommendation')
    parser.add_argument('--focus', action='append', default=[], help='Relevant project-relative text file; repeat as needed')
    parser.add_argument('--project-reviewed', action='store_true', help='Caller has read the relevant project evidence and classified the task from it')
    args = vars(parser.parse_args())
    project = args.pop('project')
    focus = args.pop('focus')
    reviewed = args.pop('project_reviewed')
    if (focus or reviewed) and not project:
        parser.error('--focus and --project-reviewed require --project')
    supplied = args.pop('available')
    available = None if supplied is None else [item.strip() for item in supplied.split(',') if item.strip()]
    try:
        context = inspect_project(project, focus) if project else None
        result = recommend(Task(**args), available)
        result['evidence_basis'] = 'task_flags_only'
        if context is not None:
            result['project_context'] = context
            # Collecting files is not the same as interpreting them.
            if not reviewed or not context['excerpts']:
                result['status'] = 'needs_project_review'
                result['model'] = result['reasoning_effort'] = None
                result['evidence_basis'] = 'collected_not_interpreted'
            else:
                result['evidence_basis'] = 'project_review_asserted_by_caller'
        else:
            result['warnings'].append('No folder identified or inspected. Prompt-only guidance from caller-supplied task flags, not a project-grounded assessment.')
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

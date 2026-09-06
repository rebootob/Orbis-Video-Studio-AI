import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NewProjectModal } from '../components/new-project/NewProjectModal';

describe('NewProjectModal', () => {
  it('switches modes and submits payload with default AUTO automation level', async () => {
    const handleCreate = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <NewProjectModal
        isOpen={true}
        onClose={handleClose}
        onCreate={handleCreate}
      />
    );

    // Switch to SHORT mode
    const shortOption = screen.getByTestId('mode-option-short');
    fireEvent.click(shortOption);

    // Fill title
    const titleInput = screen.getByTestId('project-title-input');
    fireEvent.change(titleInput, { target: { value: 'Product Launch Short' } });

    // Submit
    const submitBtn = screen.getByTestId('submit-create-project-btn');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Product Launch Short',
          video_mode: 'SHORT',
          mode_config: expect.objectContaining({
            automation_level: 'AUTO',
          }),
        })
      );
    });

    expect(handleClose).toHaveBeenCalled();
  });

  it('validates required title before submission', async () => {
    const handleCreate = vi.fn();
    render(
      <NewProjectModal
        isOpen={true}
        onClose={vi.fn()}
        onCreate={handleCreate}
      />
    );

    const submitBtn = screen.getByTestId('submit-create-project-btn');
    fireEvent.click(submitBtn);

    expect(handleCreate).not.toHaveBeenCalled();
  });
});

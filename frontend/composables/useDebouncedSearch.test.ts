import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { useDebouncedSearch } from './useDebouncedSearch'

// useDebouncedSearch registers an onBeforeUnmount cleanup, so it must run inside
// a component instance — mount a throwaway host that exposes its controls.
function mountDebounced(onInput: (value: string) => void, delay?: number) {
  return mount(
    defineComponent({
      setup() {
        return useDebouncedSearch(onInput, delay)
      },
      template: '<div />',
    }),
  )
}

describe('useDebouncedSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('emits only the latest value after the quiet window', () => {
    const onInput = vi.fn()
    const wrapper = mountDebounced(onInput, 300)

    wrapper.vm.schedule('a')
    vi.advanceTimersByTime(100)
    wrapper.vm.schedule('ab')
    vi.advanceTimersByTime(299)
    expect(onInput).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    expect(onInput).toHaveBeenCalledTimes(1)
    expect(onInput).toHaveBeenCalledWith('ab')
  })

  it('cancels a pending emit', () => {
    const onInput = vi.fn()
    const wrapper = mountDebounced(onInput, 300)

    wrapper.vm.schedule('x')
    wrapper.vm.cancel()
    vi.advanceTimersByTime(300)
    expect(onInput).not.toHaveBeenCalled()
  })

  it('cancels the pending emit on unmount', () => {
    const onInput = vi.fn()
    const wrapper = mountDebounced(onInput, 300)

    wrapper.vm.schedule('y')
    wrapper.unmount()
    vi.advanceTimersByTime(300)
    expect(onInput).not.toHaveBeenCalled()
  })
})

API reference
-------------

.. autoclass:: filternaut.FilterTree
  :members: parse

.. autoclass:: filternaut.Filter
   :members: tree_class, parse, parse_to_dict, clean

.. autoclass:: filternaut.Constraint
   :members: FilterUse, apply_constraint

.. autoclass:: filternaut.Optional
   :members: apply_constraint

.. autoclass:: filternaut.OneOf
   :members: apply_constraint

.. autoclass:: filternaut.filters.FieldFilter
   :members:

.. autoclass:: filternaut.drf.FilternautBackend
   :members:

.. autoclass:: filternaut.filters.DateTimeFilter
   :members:
